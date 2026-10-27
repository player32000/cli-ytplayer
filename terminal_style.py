"""ANSI text styling for terminals that support color output."""

import os
import sys


STYLES = {
    "title": "\033[1;36m",
    "current": "\033[1;32m",
    "selected": "\033[1;33m",
    "status": "\033[36m",
    "muted": "\033[2m",
    "success": "\033[32m",
    "warning": "\033[33m",
    "danger": "\033[31m",
    "reset": "\033[0m",
}


def supports_color(vt_enabled: bool = True) -> bool:
    """Return whether colored output is appropriate for the current terminal."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("TERM", "").lower() == "dumb":
        return False
    return sys.platform != "win32" or vt_enabled


def style(text: str, name: str, enabled: bool) -> str:
    """Wrap text in an ANSI style when terminal color is enabled."""
    if not enabled:
        return text
    return f"{STYLES[name]}{text}{STYLES['reset']}"
