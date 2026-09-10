"""Clean terminal UI and formatting utilities."""
import sys

# Terminal colors
BOLD = "\033[1m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
DIM = "\033[2m"
RESET = "\033[0m"

def banner():
    art = r"""
  ___        _ _      _                           
 | _ ) _  _ | | |__  | |   __ _ _ _  ___ ___ 
 | _ \| || || | / /  | |__/ _` | ' \/ -_|_-< 
 |___/ \_,_||_|_\_\  |____\__,_|_||_\___/__/ 
"""
    print(f"{CYAN}{BOLD}{art}{RESET}")
    print(f" {DIM}Typed Bulk Extraction (OpenCode + OpenRouter){RESET}\n")

def print_routes_table(routes: list):
    print(f"{BOLD}{'ROUTE ID':<45} {'PROVIDER':<12} {'PRICE STATE':<22} {'STATUS'}{RESET}")
    print("-" * 80)
    for r in routes:
        rid = r["id"]
        prov = r.get("provider", "unknown")
        price_state = r.get("price_state", "unknown")
        price = f"{GREEN}{price_state}{RESET}" if price_state == "price_observed_zero" else f"{YELLOW}{price_state}{RESET}"
        status = f"{GREEN}Active{RESET}" if r.get("enabled") else f"{RED}Disabled{RESET}"
        print(f"{rid:<45} {prov:<12} {price:<31} {status}")
    print()

def print_progress(current: int, total: int, prefix: str = "", suffix: str = ""):
    percent = (current / total) * 100 if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * current // total) if total > 0 else 0
    bar = "=" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r{CYAN}{prefix}{RESET} [{bar}] {percent:5.1f}% ({current}/{total}) {DIM}{suffix}{RESET}")
    sys.stdout.flush()
    if current >= total:
        print()

def success(msg: str):
    print(f"{GREEN}✔ {msg}{RESET}")

def info(msg: str):
    print(f"{CYAN}ℹ {msg}{RESET}")

def warn(msg: str):
    print(f"{YELLOW}▲ {msg}{RESET}")

def error(msg: str):
    print(f"{RED}✖ {msg}{RESET}")

def print_sessions_table(sessions: dict):
    print(f"\n{BOLD}{'SESSION ID':<22} {'WORKER':<8} {'ROUTE':<40} {'ITEMS':<8} {'STATUS'}{RESET}")
    print("-" * 90)
    for sid, s in sessions.items():
        w_id = f"#{s.get('worker_idx', 1)}"
        route = s.get('route_id', 'unknown')[:38]
        items = s.get('items_completed', 0)
        status_raw = s.get('status', 'active')
        status = f"{GREEN}{status_raw}{RESET}" if status_raw == "completed" else f"{CYAN}{status_raw}{RESET}"
        print(f"{sid:<22} {w_id:<8} {route:<40} {items:<8} {status}")
    print()
