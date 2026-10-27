"""Interactive playlist and account-access setup for the player."""

import os
import sys

from console_input import ConsoleKeyReader
from player_settings import load_saved_cookie_path, save_cookie_path
from terminal_style import style, supports_color
from windows_console import clear_console_screen


def _print_welcome() -> None:
    print("Welcome to YouTube Playlist CLI")


def _clear_screen(redraw: bool) -> None:
    if not redraw or clear_console_screen():
        return
    sys.stdout.write("\033[2J\033[H")


def _show_menu(title: str, choices: list[str], redraw: bool, error: str | None = None) -> int | None:
    use_color = supports_color(vt_enabled=sys.platform != "win32" or redraw)
    if not sys.stdin.isatty():
        _clear_screen(redraw)
        _print_welcome()
        print(f"\n{title}\n")
        for number, choice in enumerate(choices, start=1):
            print(f"  {number}. {choice}")
        print(f"  {len(choices) + 1}. Back")
        if error:
            print(f"\n{error}")
        answer = input("\nChoose an option (or type b to go back): ").strip().lower()
        if answer == "b" or answer == str(len(choices) + 1):
            return None
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return int(answer)
        return -1

    back_index = len(choices)
    selected_index = 0
    while True:
        _clear_screen(redraw)
        _print_welcome()
        print(f"\n{title}\n")
        for index, choice in enumerate(choices):
            marker = ">" if index == selected_index else " "
            option = f" {marker} {index + 1}. {choice}"
            print(style(option, "selected", use_color) if index == selected_index else option)
        marker = ">" if selected_index == back_index else " "
        back_option = f" {marker} {back_index + 1}. Back"
        print(style(back_option, "selected", use_color) if selected_index == back_index else back_option)
        if error:
            print(f"\n{error}")
        print("\nUp/Down = navigate | Enter = choose | b = back")
        sys.stdout.flush()

        with ConsoleKeyReader() as key_reader:
            while True:
                try:
                    key = key_reader.read_key()
                except KeyboardInterrupt:
                    return None
                if key == "up":
                    selected_index = max(0, selected_index - 1)
                    break
                if key == "down":
                    selected_index = min(back_index, selected_index + 1)
                    break
                if key in ("b", "escape", "ctrl-c"):
                    return None
                if key == "enter":
                    return None if selected_index == back_index else selected_index + 1
                if key and key.isdigit():
                    selection = int(key)
                    if selection == back_index + 1:
                        return None
                    if 1 <= selection <= len(choices):
                        return selection


def _choose(title: str, choices: list[str], redraw: bool) -> int | None:
    error = None
    while True:
        selection = _show_menu(title, choices, redraw, error)
        if selection != -1:
            return selection
        error = "Please enter one of the listed numbers or b."


def _ask_text(title: str, prompt: str, redraw: bool) -> str | None:
    _clear_screen(redraw)
    _print_welcome()
    print(f"\n{title}")
    print("Type b to go back.")
    answer = input(f"\n{prompt}: ").strip().strip('"')
    return None if answer.lower() == "b" else answer


def _playlist_url(redraw: bool) -> str | None:
    while True:
        _clear_screen(redraw)
        _print_welcome()
        print("\nPlaylist URL")
        print("Type b to go back.")
        url = input("\nPaste the YouTube playlist URL: ").strip()
        if url is None:
            return None
        if url.lower() == "b":
            return None
        if url.strip():
            return url.strip().strip('"')
        _clear_screen(redraw)
        _print_welcome()
        print("\nThe playlist URL cannot be empty.\n")


def _search_query(redraw: bool) -> str | None:
    while True:
        query = _ask_text("Search YouTube", "Enter a search term", redraw)
        if query is None:
            return None
        if query:
            return query
        _clear_screen(redraw)
        _print_welcome()
        print("\nThe search term cannot be empty.\n")


def _browser_name(redraw: bool) -> str | None:
    browsers = ["Chrome", "Firefox", "Edge", "Brave", "Chromium", "Other"]
    selection = _choose("Which browser already has your YouTube session?", browsers, redraw)
    if selection is None:
        return None
    if selection == len(browsers):
        browser = _ask_text("Browser name", "Enter a browser name supported by yt-dlp", redraw)
        return browser.lower() if browser else None
    return browsers[selection - 1].lower()


def _cookie_file(redraw: bool) -> str | None:
    error = None
    while True:
        _clear_screen(redraw)
        _print_welcome()
        print("\nPrepare your cookies.txt file:")
        print("  1. Sign in to YouTube in your browser.")
        print("  2. Use a trusted exporter that saves Netscape cookies.txt format.")
        print("  3. Export cookies for youtube.com (and music.youtube.com for YouTube Music).")
        print("  4. Return here and enter the full path to the file.")
        print("Review exporter permissions first. Cookies grant access to your account.")
        print("Type b to go back.")
        if error:
            print(f"\n{error}")
        path = input("\nPath to cookies.txt: ").strip().strip('"')
        if path.lower() == "b":
            return None
        if os.path.isfile(path):
            save_cookie_path(path)
            return path
        error = "That file was not found. Check the path and try again."


def _choose_authentication(
    private: bool,
    redraw: bool,
) -> tuple[str, str | None] | None:
    while True:
        choices = []
        saved_cookie_path = load_saved_cookie_path()
        if saved_cookie_path and os.path.isfile(saved_cookie_path):
            choices.append("Use the saved cookies.txt file")
        saved_path_missing = bool(saved_cookie_path and not os.path.isfile(saved_cookie_path))
        if not private:
            choices.append("Continue without account cookies (public playlist)")
        choices.extend([
            "Use a browser session where you are already signed in",
            "Load or choose another cookies.txt file",
        ])

        selection = _choose(
            "Choose how to access this playlist.\n"
            "Browser: reads an existing signed-in session.\n"
            "Cookies: loads an exported cookies.txt; no password is requested."
            + (
                "\nThe previously saved cookies.txt path no longer exists."
                if saved_path_missing
                else ""
            ),
            choices,
            redraw,
        )
        if selection is None:
            return None
        choice = choices[selection - 1]
        if choice == "Use the saved cookies.txt file":
            return "none", saved_cookie_path
        if choice == "Continue without account cookies (public playlist)":
            return "none", None
        if choice == "Use a browser session where you are already signed in":
            browser = _browser_name(redraw)
            if browser:
                return browser, None
        else:
            cookie_file = _cookie_file(redraw)
            if cookie_file:
                return "none", cookie_file


def get_interactive_player_options(redraw: bool = False) -> dict | None:
    """Ask whether to play or bulk-download a source, its format, and account access."""
    while True:
        task = _choose(
            "What would you like to do?",
            [
                "Quick YouTube search (play audio)",
                "Play a list (audio or video)",
                "Download the full list as MP3 audio",
                "Download the full list as video",
            ],
            redraw,
        )
        if task is None:
            return None
        if task == 1:
            query = _search_query(redraw)
            if query is None:
                continue
            return {
                "operation": "play",
                "mode": "audio",
                "source": "search",
                "url": query,
                "browser": "none",
                "cookies": None,
            }

        operation = "play" if task == 2 else "download"
        mode = "audio" if task in (2, 3) else "video"
        if operation == "play":
            playback_mode = _choose(
                "Choose playback mode:",
                ["Audio only", "Video with audio (opens an mpv video window)"],
                redraw,
            )
            if playback_mode is None:
                continue
            mode = "audio" if playback_mode == 1 else "video"

        selection = _choose(
            "Choose a source to play or download:",
            [
                "Search videos on YouTube",
                "A public playlist (paste its URL)",
                "A private playlist or liked items",
            ],
            redraw,
        )
        if selection is None:
            continue

        if selection == 1:
            query = _search_query(redraw)
            if query is None:
                continue
            authentication = _choose_authentication(private=False, redraw=redraw)
            if authentication is None:
                continue
            browser, cookies = authentication
            return {
                "operation": operation,
                "mode": mode,
                "source": "search",
                "url": query,
                "browser": browser,
                "cookies": cookies,
            }

        if selection == 2:
            url = _playlist_url(redraw)
            if url is None:
                continue
            authentication = _choose_authentication(private=False, redraw=redraw)
            if authentication is None:
                continue
            browser, cookies = authentication
            return {
                "operation": operation,
                "mode": mode,
                "source": "custom",
                "url": url,
                "browser": browser,
                "cookies": cookies,
            }

        while True:
            private_source = _choose(
                "Choose a private playlist:",
                [
                    "YouTube Music liked tracks",
                    "YouTube liked videos",
                    "A private playlist (paste its URL)",
                ],
                redraw,
            )
            if private_source is None:
                break

            url = None
            if private_source == 3:
                url = _playlist_url(redraw)
                if url is None:
                    continue
            authentication = _choose_authentication(private=True, redraw=redraw)
            if authentication is None:
                continue
            browser, cookies = authentication
            return {
                "operation": operation,
                "mode": mode,
                "source": {1: "lm", 2: "ll", 3: "custom"}[private_source],
                "url": url,
                "browser": browser,
                "cookies": cookies,
            }
