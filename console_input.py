"""Cross-platform immediate key input shared by menus and playback controls."""

import select
import sys
import time


class ConsoleKeyReader:
    """Read single keys while temporarily enabling raw input on Unix terminals."""

    def __init__(self) -> None:
        self._terminal_settings = None

    def __enter__(self) -> "ConsoleKeyReader":
        if sys.platform != "win32" and sys.stdin.isatty():
            import termios
            import tty

            descriptor = sys.stdin.fileno()
            self._terminal_settings = termios.tcgetattr(descriptor)
            tty.setraw(descriptor)
        return self

    def __exit__(self, exception_type, exception, traceback) -> None:
        if self._terminal_settings is not None:
            import termios

            termios.tcsetattr(
                sys.stdin.fileno(),
                termios.TCSADRAIN,
                self._terminal_settings,
            )

    def read_key(self, timeout: float | None = None) -> str | None:
        """Return a normalized key name, or None when a timed read has no input."""
        if sys.platform == "win32":
            import msvcrt

            if timeout is not None:
                deadline = time.monotonic() + timeout
                while not msvcrt.kbhit():
                    if time.monotonic() >= deadline:
                        return None
                    time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            key = msvcrt.getwch()
            if key in ("\x00", "\xe0"):
                return self._normalize_arrow(msvcrt.getwch())
            return self._normalize_character(key)

        if timeout is not None:
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if not ready:
                return None
        key = sys.stdin.read(1)
        if key == "\x1b":
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready and sys.stdin.read(1) == "[":
                ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                if ready:
                    return self._normalize_arrow(sys.stdin.read(1))
            return "escape"
        return self._normalize_character(key)

    @staticmethod
    def _normalize_arrow(key: str) -> str:
        return {
            "A": "up",
            "B": "down",
            "H": "up",
            "P": "down",
        }.get(key, "unknown")

    @staticmethod
    def _normalize_character(key: str) -> str:
        if key in ("\r", "\n"):
            return "enter"
        if key == "\x03":
            return "ctrl-c"
        return key.lower()
