"""
utils.py - Logging helpers and terminal output for DevSync.
"""

import sys

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


# ANSI colors
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"

_use_color = sys.stdout.isatty()


def _c(color: str, text: str) -> str:
    return f"{color}{text}{RESET}" if _use_color else text


def log_info(msg: str):
    print(_c(CYAN, "  •") + f" {msg}")


def log_success(msg: str):
    print(_c(GREEN, "  ✓") + f" {msg}")


def log_warn(msg: str):
    print(_c(YELLOW, "  !") + f" {msg}")


def log_error(msg: str):
    print(_c(RED, "  ✗") + f" {msg}", file=sys.stderr)


def print_banner():
    banner = r"""
  ____             ____
 |  _ \  _____   _/ ___| _   _ _ __   ___
 | | | |/ _ \ \ / /\___ \| | | | '_ \ / __|
 | |_| |  __/\ V /  ___) | |_| | | | | (__
 |____/ \___| \_/  |____/ \__, |_| |_|\___|
                           |___/
"""
    if _use_color:
        print(_c(CYAN, banner))
    else:
        print(banner)

    print(f"  {_c(BOLD, 'PC → Android file sync over WiFi — no USB needed')}\n")
