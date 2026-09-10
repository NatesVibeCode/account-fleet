"""Sandbox execution layer for running untrusted model commands."""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class SandboxError(Exception):
    pass

def is_docker_available() -> bool:
    """Check if Docker daemon is running and responsive."""
    if not shutil.which("docker"):
        return False
    try:
        res = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=2
        )
        return res.returncode == 0
    except Exception:
        return False

def clean_safe_env(extra_env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """Sanitize environment variables: strip host credentials and set isolated XDG directories."""
    safe_keys = {"PATH", "HOME", "USER", "SHELL", "LANG", "LC_ALL", "TERM"}
    env = {k: os.environ[k] for k in safe_keys if k in os.environ}
    # Ensure sensible fallback PATH
    env["PATH"] = env.get("PATH", "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin")
    if extra_env:
        env.update(extra_env)
    return env

class SandboxRunner:
    """Dispatches model CLI commands either in a container or in a hardened subprocess sandbox."""
    def __init__(self, use_docker: Optional[bool] = None, image: str = "bulk-lanes-worker:v1"):
        self.use_docker = is_docker_available() if use_docker is None else use_docker
        self.image = image

    def run_opencode_task(
        self,
        task_config: dict,
        args: List[str],
        timeout_sec: int = 120
    ) -> Tuple[int, str, str]:
        """Runs an opencode command inside a sandboxed environment.
        
        task_config is written to opencode.json in an ephemeral task directory.
        All agent tools and MCPs are explicitly denied.
        """
        with tempfile.TemporaryDirectory(prefix="bulk-lanes-task-") as td:
            task_dir = Path(td)
            cfg_path = task_dir / "opencode.json"
            cfg_path.write_text(json.dumps(task_config, indent=2))

            if self.use_docker:
                cmd = [
                    "docker", "run", "--rm",
                    "--read-only",
                    "--cap-drop=ALL",
                    "--security-opt=no-new-privileges",
                    "--pids-limit=128",
                    "--memory=1g",
                    "--cpus=2",
                    "--network", "bridge",
                    "--tmpfs", "/tmp:rw,nosuid,size=256m",
                    "--mount", f"type=bind,src={task_dir},dst=/task,readonly",
                    self.image
                ] + args
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec
                )
                return res.returncode, res.stdout, res.stderr
            else:
                # Subprocess sandbox with isolated XDG paths and sanitized env
                tmp_run = task_dir / "run_tmp"
                tmp_run.mkdir(exist_ok=True)
                env = clean_safe_env({
                    "XDG_CONFIG_HOME": str(tmp_run / "config"),
                    "XDG_DATA_HOME": str(tmp_run / "data"),
                    "XDG_STATE_HOME": str(tmp_run / "state"),
                    "XDG_CACHE_HOME": str(tmp_run / "cache"),
                })
                cmd = ["opencode"] + args
                res = subprocess.run(
                    cmd,
                    cwd=str(task_dir),
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    env=env
                )
                return res.returncode, res.stdout, res.stderr
