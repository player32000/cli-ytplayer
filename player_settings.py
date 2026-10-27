"""Local, non-secret settings for YouTube Playlist CLI."""

import json
import os
import sys


def _settings_file() -> str:
    if sys.platform == "win32":
        base_directory = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base_directory, "YouTubePlaylistCLI", "settings.json")

    base_directory = os.environ.get(
        "XDG_CONFIG_HOME",
        os.path.join(os.path.expanduser("~"), ".config"),
    )
    return os.path.join(base_directory, "youtube-playlist-cli", "settings.json")


def load_saved_cookie_path() -> str | None:
    """Return the remembered cookie-file path, reporting unreadable settings."""
    settings_file = _settings_file()
    if not os.path.isfile(settings_file):
        return None

    try:
        with open(settings_file, encoding="utf-8") as file:
            settings = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        print(f"Warning: could not read local player settings: {error}")
        return None

    cookie_path = settings.get("cookie_file") if isinstance(settings, dict) else None
    return cookie_path if isinstance(cookie_path, str) and cookie_path else None


def save_cookie_path(cookie_path: str) -> None:
    """Remember only the cookie-file location, never its contents."""
    settings_file = _settings_file()
    try:
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        with open(settings_file, "w", encoding="utf-8") as file:
            json.dump({"cookie_file": os.path.abspath(cookie_path)}, file, indent=2)
    except OSError as error:
        print(f"Warning: could not save the cookie-file path: {error}")
