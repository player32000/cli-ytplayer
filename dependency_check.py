"""Runtime dependency checks and actionable installation guidance."""

import re
import shutil
import subprocess
import sys
from functools import lru_cache

from terminal_style import style, supports_color


MINIMUM_RUNTIME_VERSIONS = {
    "node": (22,),
    "deno": (2, 3),
}

RUNTIME_PURPOSES = {
    "node": "yt-dlp uses it to solve YouTube's JavaScript challenge and read media formats.",
    "deno": "yt-dlp uses it to solve YouTube's JavaScript challenge and read media formats.",
}


def _print_guidance(message: str) -> None:
    """Highlight URLs in setup guidance when the terminal supports ANSI color."""
    parts = re.split(r"(https?://\S+)", message)
    highlighted = "".join(
        style(part, "status", supports_color())
        if part.startswith(("https://", "http://"))
        else part
        for part in parts
    )
    print(highlighted)


def report_missing_python_package(package: str, install_command: str, purpose: str) -> None:
    print(f"Missing Python package: {package}.")
    print(f"Purpose: {purpose}")
    print(f"Install it with: {install_command}")


def _runtime_version(executable: str) -> tuple[int, ...] | None:
    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", f"{result.stdout}\n{result.stderr}")
    if result.returncode != 0 or not match:
        return None
    return tuple(int(part) for part in match.groups() if part is not None)


def _is_version_at_least(version: tuple[int, ...], minimum: tuple[int, ...]) -> bool:
    padded_version = version + (0,) * (len(minimum) - len(version))
    return padded_version >= minimum


def _runtime_install_guidance(runtime: str) -> str:
    if runtime == "node":
        if sys.platform == "win32":
            return "Install Node.js 22+ from https://nodejs.org/ or run: winget install OpenJS.NodeJS.LTS"
        if sys.platform == "darwin":
            return "Install Node.js 22+ from https://nodejs.org/ or run: brew install node"
        return "Install Node.js 22+ from https://nodejs.org/"
    if sys.platform == "win32":
        return "Install Deno 2.3+ from https://deno.com/ or run: winget install DenoLand.Deno"
    if sys.platform == "darwin":
        return "Install Deno 2.3+ from https://deno.com/ or run: brew install deno"
    return "Install Deno 2.3+ from https://deno.com/"


@lru_cache(maxsize=1)
def supported_javascript_runtimes() -> list[str]:
    """Return supported JavaScript runtimes, preferring Node.js to match yt-dlp defaults."""
    supported = []
    for runtime, minimum in MINIMUM_RUNTIME_VERSIONS.items():
        executable = shutil.which(runtime)
        if not executable:
            continue
        version = _runtime_version(executable)
        if version and _is_version_at_least(version, minimum):
            supported.append(runtime)
    return supported


def has_javascript_runtime() -> bool:
    """Check that Node.js 22+ or Deno 2.3+ is available to yt-dlp."""
    if supported_javascript_runtimes():
        return True

    installed = []
    for runtime, minimum in MINIMUM_RUNTIME_VERSIONS.items():
        executable = shutil.which(runtime)
        if not executable:
            continue
        version = _runtime_version(executable)
        version_text = ".".join(map(str, version)) if version else "unknown version"
        installed.append((runtime, version_text, minimum))

    if not installed:
        print("A JavaScript runtime is missing.")
        print("Purpose: yt-dlp needs one to pass YouTube's JavaScript challenge and read available formats.")
        _print_guidance(_runtime_install_guidance("node"))
        _print_guidance(_runtime_install_guidance("deno"))
        return False

    print("No supported JavaScript runtime was found.")
    for runtime, version_text, minimum in installed:
        minimum_text = ".".join(map(str, minimum))
        print(f"Found {runtime} {version_text}; TubeQueue requires {runtime} {minimum_text} or later.")
        print(f"Purpose: {RUNTIME_PURPOSES[runtime]}")
        _print_guidance(_runtime_install_guidance(runtime))
    return False


def check_runtime_dependencies(operation: str) -> bool:
    """Check YouTube's JavaScript runtime and the download-only FFmpeg dependency."""
    ready = has_javascript_runtime()
    ffmpeg_available = shutil.which("ffmpeg") is not None

    if operation == "download" and not ffmpeg_available:
        print("FFmpeg is missing.")
        print("Purpose: it converts audio downloads to MP3 and merges separate video/audio streams.")
        _print_guidance(
            "Install FFmpeg from https://ffmpeg.org/download.html and add its bin folder to PATH."
        )
        ready = False
    elif operation == "play" and not ffmpeg_available:
        print("Optional feature unavailable: FFmpeg was not found on PATH.")
        print("Purpose: FFmpeg enables MP3 conversion and merging audio/video downloads.")
        _print_guidance(
            "Install it from https://ffmpeg.org/download.html and add its bin folder to PATH."
        )

    return ready


def check_python_version() -> bool:
    """Report when the running interpreter is below the project's minimum."""
    if sys.version_info >= (3, 10):
        return True
    print(f"Python {sys.version_info.major}.{sys.version_info.minor} is installed; TubeQueue requires Python 3.10 or later.")
    print("Purpose: Python runs TubeQueue and its command-line player/downloader.")
    _print_guidance(
        "Install Python from https://www.python.org/downloads/ and enable its PATH option."
    )
    return False
