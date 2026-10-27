"""Windows-only console helpers used by the playlist player."""

import ctypes
import sys
from ctypes import wintypes


class _Coord(ctypes.Structure):
    _fields_ = [("X", wintypes.SHORT), ("Y", wintypes.SHORT)]


class _SmallRect(ctypes.Structure):
    _fields_ = [
        ("Left", wintypes.SHORT),
        ("Top", wintypes.SHORT),
        ("Right", wintypes.SHORT),
        ("Bottom", wintypes.SHORT),
    ]


class _ConsoleScreenBufferInfo(ctypes.Structure):
    _fields_ = [
        ("dwSize", _Coord),
        ("dwCursorPosition", _Coord),
        ("wAttributes", wintypes.WORD),
        ("srWindow", _SmallRect),
        ("dwMaximumWindowSize", _Coord),
    ]


def has_console_output() -> bool:
    """Return whether stdout is connected to a Windows console screen buffer."""
    if sys.platform != "win32":
        return False

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetConsoleMode.restype = wintypes.BOOL
    handle = kernel32.GetStdHandle(-11)
    mode = wintypes.DWORD()
    return bool(handle and kernel32.GetConsoleMode(handle, ctypes.byref(mode)))


def clear_console_screen() -> bool:
    """Clear the Windows console screen buffer and move the cursor to its origin."""
    if sys.platform != "win32":
        return False

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetConsoleScreenBufferInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(_ConsoleScreenBufferInfo),
    ]
    kernel32.GetConsoleScreenBufferInfo.restype = wintypes.BOOL
    kernel32.FillConsoleOutputCharacterW.argtypes = [
        wintypes.HANDLE,
        wintypes.WCHAR,
        wintypes.DWORD,
        _Coord,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.FillConsoleOutputCharacterW.restype = wintypes.BOOL
    kernel32.FillConsoleOutputAttribute.argtypes = [
        wintypes.HANDLE,
        wintypes.WORD,
        wintypes.DWORD,
        _Coord,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.FillConsoleOutputAttribute.restype = wintypes.BOOL
    kernel32.SetConsoleCursorPosition.argtypes = [wintypes.HANDLE, _Coord]
    kernel32.SetConsoleCursorPosition.restype = wintypes.BOOL
    handle = kernel32.GetStdHandle(-11)
    if not handle:
        return False

    screen_info = _ConsoleScreenBufferInfo()
    if not kernel32.GetConsoleScreenBufferInfo(handle, ctypes.byref(screen_info)):
        return False

    cell_count = screen_info.dwSize.X * screen_info.dwSize.Y
    origin = _Coord(0, 0)
    cells_written = wintypes.DWORD()
    if not kernel32.FillConsoleOutputCharacterW(
        handle, " ", cell_count, origin, ctypes.byref(cells_written)
    ):
        return False
    if not kernel32.FillConsoleOutputAttribute(
        handle,
        screen_info.wAttributes,
        cell_count,
        origin,
        ctypes.byref(cells_written),
    ):
        return False
    return bool(kernel32.SetConsoleCursorPosition(handle, origin))


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


def enable_virtual_terminal():
    """Enable ANSI screen updates in a Windows console and return a restore function."""
    if sys.platform != "win32":
        return None

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel32.GetStdHandle.restype = wintypes.HANDLE
    kernel32.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetConsoleMode.restype = wintypes.BOOL
    kernel32.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.SetConsoleMode.restype = wintypes.BOOL

    handle = kernel32.GetStdHandle(-11)
    original_mode = wintypes.DWORD()
    if not handle or not kernel32.GetConsoleMode(handle, ctypes.byref(original_mode)):
        return None

    enable_virtual_terminal_processing = 0x0004
    if not kernel32.SetConsoleMode(
        handle,
        original_mode.value | enable_virtual_terminal_processing,
    ):
        return None

    return lambda: kernel32.SetConsoleMode(handle, original_mode.value)
