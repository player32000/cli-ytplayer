"""Windows-only console helpers used by the playlist player."""

import ctypes
import sys
from ctypes import wintypes


def disable_quick_edit():
    """Disable console text selection temporarily and return a restore function."""
    if sys.platform != "win32":
        return None

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetConsoleMode.restype = wintypes.BOOL
    kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetConsoleMode.restype = wintypes.BOOL

    # Keep the original settings so the console is restored when playback ends.
    handle = kernel32.GetStdHandle(-10)
    original_mode = wintypes.DWORD()
    if not handle or not kernel32.GetConsoleMode(handle, ctypes.byref(original_mode)):
        print("Warning: could not configure console selection mode.")
        return None

    enable_quick_edit_mode = 0x0040
    enable_extended_flags = 0x0080
    player_mode = (original_mode.value | enable_extended_flags) & ~enable_quick_edit_mode
    if not kernel32.SetConsoleMode(handle, player_mode):
        print("Warning: could not disable console Quick Edit mode.")
        return None

    return lambda: kernel32.SetConsoleMode(handle, original_mode.value)


def read_windows_controls(commands) -> None:
    """Read Windows key presses immediately and pass them to the player."""
    import msvcrt

    while True:
        try:
            key = msvcrt.getwch()
        except KeyboardInterrupt:
            commands.put("q")
            return
        if key in ("\x00", "\xe0"):
            msvcrt.getwch()
        elif key == "\x03":
            commands.put("q")
            return
        elif key == "\r":
            commands.put("")
        else:
            command = key.lower()
            commands.put(command)
            if command == "q":
                return
