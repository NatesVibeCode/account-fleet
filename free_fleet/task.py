"""Declarative task contract loading."""
from pathlib import Path

from .models import TaskSpec


def load_task_spec(task_path: str | Path) -> TaskSpec:
    path = Path(task_path)
    if path.suffix.lower() != ".json":
        raise ValueError("task specs must be JSON files")
    if not path.is_file():
        raise FileNotFoundError(f"task file not found: {path}")
    return TaskSpec.model_validate_json(path.read_text())
