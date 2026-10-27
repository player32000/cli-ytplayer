#!/usr/bin/env python3
"""
player.py

Command-line playlist player. Streams tracks one at a time with mpv instead
of downloading the whole playlist in advance. The current track can also be
downloaded as MP3 audio or video.

Requirements:
    python -m pip install -U "yt-dlp[default]"
    Node.js 22+ or Deno 2.3+ on PATH for YouTube's JavaScript challenge
    mpv compatible with your CPU
    ffmpeg on PATH for MP3 downloads

Cookies are not discovered automatically. Pass a Netscape-format cookie file
with --cookies, or omit it to use the browser selected with --browser.

Controls are read directly without Enter in interactive terminals. The shared
keyboard reader is in console_input.py; Windows screen and selection settings
are managed by windows_console.py.
"""

import argparse
import atexit
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from collections import deque

try:
    import yt_dlp
except ImportError:
    from dependency_check import report_missing_python_package

    report_missing_python_package(
        "yt-dlp",
        'python -m pip install -r requirements.txt',
        "TubeQueue uses it to search YouTube, read playlists, stream, and download media.",
    )
    sys.exit(1)

from dependency_check import check_python_version, check_runtime_dependencies
from download_playlist import (
    add_common_arguments,
    cookie_options,
    get_source_config,
    youtube_javascript_options,
)
from console_input import ConsoleKeyReader
from download_manager import download_full_list, start_download_queue
from interactive_setup import get_interactive_player_options
from playlist_navigation import PlaylistNavigation
from playlist_view import (
    display_playlist,
    update_audio_meter_line,
    update_playback_time_line,
)
from terminal_style import style, supports_color
from windows_console import (
    disable_quick_edit,
    enable_virtual_terminal,
    has_console_output,
)


SEARCH_RESULT_LIMIT = 20
METER_REFRESH_INTERVAL = 1 / 40
INPUT_POLL_INTERVAL = 1 / 100
_ACTIVE_PLAYBACK: subprocess.Popen | None = None


def stop_active_playback() -> None:
    """Stop mpv during shutdown so it cannot continue after the CLI exits."""
    global _ACTIVE_PLAYBACK
    process = _ACTIVE_PLAYBACK
    if process is None:
        return
    if process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
        except OSError as error:
            print(f"\nWarning: could not stop mpv during shutdown: {error}")
    _ACTIVE_PLAYBACK = None


def clear_active_playback(process: subprocess.Popen) -> None:
    """Forget a player process that has already exited or been stopped."""
    global _ACTIVE_PLAYBACK
    if _ACTIVE_PLAYBACK is process:
        _ACTIVE_PLAYBACK = None
        atexit.unregister(stop_active_playback)


def list_tracks(config: dict, browser: str, cookie_file: str) -> list:
    """Get each track's ID, title, and URL without downloading the media."""
    options = {"quiet": True, "extract_flat": True, "skip_download": True}
    options.update(youtube_javascript_options())
    options.update(cookie_options(browser, cookie_file))
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(config["url"], download=False)

    # Keep only what the player needs later: a readable title and a watch URL.
    tracks = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        video_id = entry.get("id")
        tracks.append({
            "title": entry.get("title") or video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "duration": entry.get("duration"),
        })
    return tracks


def build_search_config(query: str) -> dict:
    """Create a bounded yt-dlp search source and download destination."""
    return {
        "url": f"ytsearch{SEARCH_RESULT_LIMIT}:{query}",
        "folder": "descargas_busqueda",
        "filename_template": "%(artist,uploader)s - %(title)s.%(ext)s",
        "source_label": f"YouTube search: {query}",
    }


def find_mpv() -> str | None:
    """Find the mpv program, checking the local copy before installed locations."""
    if sys.platform == "win32":
        script_folder = os.path.dirname(os.path.abspath(__file__))
        portable = os.path.join(script_folder, "mpv-portable", "mpv.exe")
        if os.path.isfile(portable):
            return portable

    executable = shutil.which("mpv")
    if executable:
        return executable

    if sys.platform == "win32":
        directories = [
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ]
        for directory in directories:
            if directory:
                candidate = os.path.join(directory, "MPV Player", "mpv.exe")
                if os.path.isfile(candidate):
                    return candidate

    return None


def print_terminal_link(url: str) -> None:
    """Make URLs stand out in terminals that support ANSI colors."""
    print(style(url, "status", supports_color()))


def get_media_stream(
    url: str,
    browser: str,
    cookie_file: str,
    mode: str,
) -> tuple[str, dict]:
    """Ask yt-dlp for a playable audio or combined audio/video URL."""
    options = {
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio/best" if mode == "audio" else "best[height<=1080]/best",
    }
    options.update(youtube_javascript_options())
    options.update(cookie_options(browser, cookie_file))
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return info["url"], info.get("http_headers", {})


def resolve_media_stream(
    result: queue.Queue,
    url: str,
    browser: str,
    cookie_file: str,
    mode: str,
) -> None:
    """Resolve the selected media in the background to keep controls responsive."""
    try:
        result.put((True, get_media_stream(url, browser, cookie_file, mode)))
    except Exception as error:
        result.put((False, error))


def is_unavailable_video_error(error: Exception) -> bool:
    """Identify YouTube errors that mean this playlist item cannot be played."""
    message = str(error).lower()
    return "video unavailable" in message or "this video is not available" in message


def is_cookie_access_error(error: Exception) -> bool:
    """Recognize common browser-cookie and expired-session errors."""
    message = str(error).lower()
    indicators = (
        "cookie",
        "dpapi",
        "decrypt",
        "sign in",
        "sign-in",
        "login required",
        "authentication",
        "private video",
    )
    return any(indicator in message for indicator in indicators)


def mpv_supports_audio_meter(mpv_executable: str) -> bool:
    """Check that this mpv build exposes the FFmpeg filter bridge used by the meter."""
    try:
        result = subprocess.run(
            [mpv_executable, "--af=help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"Could not check mpv audio-filter support: {error}")
        return False
    return result.returncode == 0 and "lavfi" in f"{result.stdout}\n{result.stderr}".lower()


def start_playback(
    url: str,
    mpv_executable: str,
    headers: dict,
    mode: str,
    enable_audio_meter: bool,
) -> tuple[subprocess.Popen, deque[str], threading.Thread, queue.Queue, threading.Thread | None]:
    """Start mpv with the selected media; it is not saved to disk."""
    global _ACTIVE_PLAYBACK
    command = [mpv_executable, "--input-terminal=no"]
    if enable_audio_meter:
        command.append(
            "--af=lavfi=[asetnsamples=n=1024:p=0,astats=metadata=1:reset=1,"
            "ametadata=mode=print:key=lavfi.astats.Overall.RMS_level:file=-:direct=1]"
        )
    if mode == "audio":
        command.append("--no-video")
    else:
        command.append("--input-vo-keyboard=no")
    if headers:
        # Pass YouTube's request details to mpv so the stream can be opened.
        fields = []
        for name, value in headers.items():
            escaped_value = value.replace("\\", "\\\\").replace(",", "\\,")
            fields.append(f"{name}: {escaped_value}")
        command.append(f"--http-header-fields={','.join(fields)}")
    command.append(url)
    process_options = {
        "stdin": subprocess.DEVNULL,
        "stderr": subprocess.PIPE,
        "stdout": subprocess.PIPE if enable_audio_meter else subprocess.DEVNULL,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if sys.platform == "win32":
        process_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(command, **process_options)
    _ACTIVE_PLAYBACK = process
    atexit.register(stop_active_playback)
    error_lines = deque(maxlen=40)

    def collect_error_output() -> None:
        if process.stderr is None:
            return
        for line in process.stderr:
            error_lines.append(line.rstrip())

    error_reader = threading.Thread(target=collect_error_output, daemon=True)
    error_reader.start()
    audio_levels = queue.Queue(maxsize=1)

    if not enable_audio_meter:
        return process, error_lines, error_reader, audio_levels, None

    def collect_audio_levels() -> None:
        if process.stdout is None:
            return
        for line in process.stdout:
            prefix = "lavfi.astats.Overall.RMS_level="
            if not line.startswith(prefix):
                continue
            try:
                level = float(line[len(prefix):].strip())
            except ValueError:
                continue
            if audio_levels.full():
                try:
                    audio_levels.get_nowait()
                except queue.Empty:
                    pass
            try:
                audio_levels.put_nowait(level)
            except queue.Full:
                pass

    audio_reader = threading.Thread(target=collect_audio_levels, daemon=True)
    audio_reader.start()
    return process, error_lines, error_reader, audio_levels, audio_reader


def read_controls(commands: queue.Queue) -> None:
    """Read navigation and playback controls in the background."""
    if sys.stdin.isatty():
        try:
            with ConsoleKeyReader() as key_reader:
                while True:
                    key = key_reader.read_key(timeout=0.1)
                    if key is None:
                        continue
                    if key == "enter":
                        commands.put("")
                    elif key == "ctrl-c":
                        commands.put("q")
                        return
                    elif key in ("up", "down"):
                        commands.put(key)
                    else:
                        command = key.lower()
                        commands.put(command)
                        if command == "q":
                            return
        except KeyboardInterrupt:
            commands.put("q")
        return

    while True:
        try:
            command = input("   > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            commands.put("q")
            return
        commands.put(command)
        if command == "q":
            return


def main() -> None:
    if not check_python_version():
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Command-line playlist player with on-demand downloads.")
    add_common_arguments(parser)
    parser.add_argument(
        "--show-stream-url-on-error",
        action="store_true",
        help="Print the full, temporary media stream URL if mpv fails",
    )
    parser.add_argument(
        "--mode",
        choices=["audio", "video"],
        default="audio",
        help="Play audio only or show video in an mpv window (default: audio)",
    )
    parser.add_argument(
        "--search",
        metavar="QUERY",
        help=f"Search YouTube and show up to {SEARCH_RESULT_LIMIT} results",
    )
    parser.add_argument(
        "--download-playlist",
        action="store_true",
        help="Download the full source as MP3 or video instead of playing it",
    )
    meter_options = parser.add_mutually_exclusive_group()
    meter_options.add_argument(
        "--meter",
        dest="meter",
        action="store_true",
        help="Show the real-time audio RMS meter (also toggle with m during playback)",
    )
    meter_options.add_argument(
        "--no-meter",
        dest="meter",
        action="store_false",
        help="Hide the real-time audio RMS meter",
    )
    parser.set_defaults(meter=True)
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored terminal output",
    )
    menu_terminal_restore = None
    if len(sys.argv) == 1:
        if sys.platform == "win32" and sys.stdout.isatty():
            menu_terminal_restore = enable_virtual_terminal()
            if menu_terminal_restore:
                atexit.register(menu_terminal_restore)
        args = parser.parse_args([])
        menu_redraw = sys.stdout.isatty() and (
            sys.platform != "win32" or bool(menu_terminal_restore)
        )
        try:
            menu_options = get_interactive_player_options(redraw=menu_redraw)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            return
        if menu_options is None:
            print("Goodbye!")
            return
        for name, value in menu_options.items():
            setattr(args, name, value)
    else:
        args = parser.parse_args()

    operation = getattr(args, "operation", "download" if args.download_playlist else "play")
    if args.download_playlist:
        operation = "download"

    if not check_runtime_dependencies(operation):
        sys.exit(1)

    mpv_executable = None
    if operation == "play":
        mpv_executable = find_mpv()
        if not mpv_executable:
            print("mpv was not found.")
            print("Purpose: mpv plays the audio/video stream; it is not needed for playlist downloads.")
            print("(Windows: winget install --id shinchiro.mpv --exact --source winget)")
            print("(macOS: brew install mpv | Linux: use your distribution's package manager)")
            sys.exit(1)

    # "args" holds the user's command-line choices; "config" describes the playlist.
    if args.search is not None:
        if not args.search.strip():
            parser.error("--search requires a non-empty query.")
        if args.url or args.source != "lm":
            parser.error("--search cannot be combined with --source or --url.")
        config = build_search_config(args.search.strip())
    elif args.source == "search":
        if not args.url or not args.url.strip():
            parser.error("A search term is required.")
        config = build_search_config(args.url.strip())
    else:
        try:
            config = get_source_config(args.source, args.url, args.browser, args.cookies)
        except ValueError as error:
            parser.error(str(error))

    source_label = config.get("source_label", f"{args.source} ({config['url']})")
    is_search = args.source == "search" or args.search is not None
    print(f"Source: {source_label}")
    if operation == "download":
        print(f"Cookie file: {args.cookies}" if args.cookies else f"Browser cookies: {args.browser}")
        try:
            download_full_list(config, args.mode, args.browser, args.cookies)
        except (yt_dlp.utils.DownloadError, yt_dlp.cookies.CookieLoadError) as error:
            print(f"\nCould not download the full list: {error}")
            if args.cookies or args.browser != "none":
                print(
                    "If you use account cookies, they may have expired or could "
                    "not be read. Sign in again and export a fresh cookies.txt file."
                )
            sys.exit(1)
        return

    # Playback requires mpv; bulk downloading does not.
    meter_supported = mpv_supports_audio_meter(mpv_executable)
    if not meter_supported:
        print(
            "This mpv build does not expose FFmpeg audio filters; "
            "the live audio meter is unavailable. Playback can still work without it."
        )
        print(
            "To enable the meter, install an mpv build that includes the "
            "'lavfi' audio filter, or start TubeQueue with --no-meter."
        )
        print("Find mpv builds at:")
        print_terminal_link("https://mpv.io/installation/")

    print("Loading YouTube search results..." if is_search else "Loading playlist...")
    # "tracks" is the ordered list of titles and URLs used during playback.
    try:
        tracks = list_tracks(config, args.browser, args.cookies)
    except (yt_dlp.utils.DownloadError, yt_dlp.cookies.CookieLoadError) as error:
        source_name = "search results" if is_search else "playlist"
        print(f"\nCould not load the {source_name}: {error}")
        if args.cookies or args.browser != "none":
            print(
                "If you use account cookies, they may have expired or could not "
                "be read. Sign in again and export a fresh cookies.txt file."
            )
        sys.exit(1)
    if not tracks:
        print("No search results found." if is_search else "No tracks found.")
        return
    item_label = "results" if is_search else "tracks"
    print(f"{len(tracks)} {item_label} found.\n")

    # On Windows, prepare screen updates and restore console settings on exit.
    restore_console = []
    if sys.platform == "win32":
        quick_edit_restore = disable_quick_edit()
        terminal_restore = (
            enable_virtual_terminal()
            if sys.stdout.isatty() and not menu_terminal_restore
            else None
        )
        if quick_edit_restore:
            restore_console.append(quick_edit_restore)
        if terminal_restore:
            restore_console.append(terminal_restore)
    for restore in restore_console:
        atexit.register(restore)

    def restore_console_settings() -> None:
        for restore in restore_console:
            atexit.unregister(restore)
            try:
                restore()
            except OSError as error:
                print(f"\nWarning: could not restore console settings: {error}")

    redraw_terminal = (
        has_console_output()
        if sys.platform == "win32"
        else sys.stdout.isatty()
    )
    ansi_terminal = redraw_terminal and (
        sys.platform != "win32" or bool(menu_terminal_restore or terminal_restore)
    )
    use_color = not args.no_color and supports_color(
        vt_enabled=ansi_terminal
    )

    # The reader thread collects keys while this main thread manages playback.
    commands = queue.Queue()
    threading.Thread(target=read_controls, args=(commands,), daemon=True).start()
    download_jobs, download_results = start_download_queue(
        config, args.browser, args.cookies
    )

    navigation = PlaylistNavigation(len(tracks))
    repeat_current = False
    show_help = False
    show_meter = args.meter and meter_supported
    if args.meter and not meter_supported:
        print("Starting without the requested meter.")
    playback_status = "Preparing audio..."
    playback_started_at = None
    elapsed_seconds = 0.0
    audio_level_db = None

    def refresh_view() -> None:
        display_playlist(
            tracks,
            navigation.index,
            navigation.selected_index,
            f"{playback_status} | Repeat: {'on' if repeat_current else 'off'} | "
            f"Shuffle: {'on' if navigation.shuffle_enabled else 'off'} | Press h for help",
            show_help,
            redraw_terminal,
            list_label="Search results" if is_search else "Playlist",
            use_color=use_color,
            elapsed_seconds=elapsed_seconds,
            duration_seconds=tracks[navigation.index].get("duration"),
            audio_level_db=audio_level_db,
            show_meter=show_meter,
            meter_available=meter_supported,
        )

    def refresh_download_results() -> None:
        nonlocal playback_status
        while True:
            try:
                title, mode, succeeded, _ = download_results.get_nowait()
            except queue.Empty:
                return
            result = "Download complete" if succeeded else "Download failed"
            format_label = "MP3" if mode == "audio" else "video"
            playback_status = f"{result} ({format_label}): {title}"
            refresh_view()

    while navigation.index < len(tracks):
        # "track" is the item at the current position in the playlist.
        track = tracks[navigation.index]
        playback_status = "Preparing audio..."
        playback_started_at = None
        elapsed_seconds = 0.0
        audio_level_db = None
        refresh_view()

        # Resolve the stream in the background so next/previous work during loading.
        stream_result = queue.Queue(maxsize=1)
        resolver = threading.Thread(
            target=resolve_media_stream,
            args=(stream_result, track["url"], args.browser, args.cookies, args.mode),
            daemon=True,
        )
        resolver.start()
        action = None
        while resolver.is_alive():
            refresh_download_results()
            try:
                command = commands.get(timeout=0.2)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                print("\nGoodbye!")
                restore_console_settings()
                return

            if command == "":
                action = "select"
                break
            elif command == "h":
                show_help = not show_help
                refresh_view()
            elif command == "m":
                if meter_supported:
                    show_meter = not show_meter
                    refresh_view()
            elif command == "up":
                navigation.move_selection(-1)
                refresh_view()
            elif command == "down":
                navigation.move_selection(1)
                refresh_view()
            elif command == "p":
                action = "previous"
                break
            elif command == "n":
                action = "next"
                break
            elif command == "r":
                repeat_current = not repeat_current
                refresh_view()
            elif command == "s":
                navigation.toggle_shuffle()
                refresh_view()
            elif command in ("a", "v"):
                download_mode = "audio" if command == "a" else "video"
                download_jobs.put((track["url"], track["title"], download_mode))
                print(f"\nQueued {download_mode} download: {track['title']}")
            elif command == "q":
                print("\nGoodbye!")
                sys.exit(0)

        if action == "previous":
            navigation.previous()
            continue
        elif action == "next":
            navigation.next()
            continue
        elif action == "select":
            navigation.select()
            continue

        succeeded, stream_result_value = stream_result.get()
        if not succeeded:
            error = stream_result_value
            if isinstance(error, yt_dlp.utils.DownloadError) and is_unavailable_video_error(error):
                print(f"\nSkipping unavailable track: {track['title']}")
                navigation.next()
                continue

            print(f"\nCould not prepare media: {error}")
            if is_cookie_access_error(error):
                print(
                    "If you use account cookies, they may have expired or could "
                    "not be read. Sign in again and export a fresh cookies.txt file."
                )
            if isinstance(error, yt_dlp.utils.DownloadError):
                if not is_cookie_access_error(error):
                    print('Update yt-dlp and its components: python -m pip install -U "yt-dlp[default]"')
                    print("You also need Deno 2.3.0+ or Node.js 22.0.0+ on PATH.")
            sys.exit(1)
        stream_url, headers = stream_result_value

        playback_status = f"Now playing ({args.mode})"
        refresh_view()
        process, mpv_errors, error_reader, audio_levels, audio_reader = start_playback(
            stream_url,
            mpv_executable,
            headers,
            args.mode,
            meter_supported,
        )
        playback_started_at = time.monotonic()
        elapsed_seconds = 0.0
        audio_level_db = None
        last_view_refresh = 0.0
        last_terminal_size = shutil.get_terminal_size()
        next_meter_refresh = playback_started_at
        meter_needs_refresh = False
        # "action" records a manual next/previous request; None means playback ended naturally.
        action = None

        # Check for key presses while mpv is still playing this track.
        while process.poll() is None:
            refresh_download_results()
            terminal_size = shutil.get_terminal_size()
            if redraw_terminal and terminal_size != last_terminal_size:
                refresh_view()
                last_terminal_size = terminal_size
                last_view_refresh = time.monotonic()
                meter_needs_refresh = False
            if meter_supported:
                updated_level = False
                try:
                    while True:
                        audio_level_db = audio_levels.get_nowait()
                        updated_level = True
                except queue.Empty:
                    pass
                if updated_level:
                    meter_needs_refresh = True
                now = time.monotonic()
                if (
                    meter_needs_refresh
                    and show_meter
                    and ansi_terminal
                    and now >= next_meter_refresh
                ):
                    update_audio_meter_line(audio_level_db, use_color)
                    meter_needs_refresh = False
                    next_meter_refresh += METER_REFRESH_INTERVAL
                    while next_meter_refresh <= now:
                        next_meter_refresh += METER_REFRESH_INTERVAL
            elapsed_seconds = time.monotonic() - playback_started_at
            if ansi_terminal and time.monotonic() - last_view_refresh >= 1.0:
                update_playback_time_line(
                    elapsed_seconds,
                    tracks[navigation.index].get("duration"),
                )
                last_view_refresh = time.monotonic()
            try:
                command = commands.get(timeout=INPUT_POLL_INTERVAL)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                clear_active_playback(process)
                print("\nGoodbye!")
                restore_console_settings()
                return

            if command == "":
                action = "select"
                break
            elif command == "h":
                show_help = not show_help
                refresh_view()
            elif command == "m":
                if meter_supported:
                    show_meter = not show_meter
                    refresh_view()
                    if show_meter:
                        meter_needs_refresh = False
                        next_meter_refresh = time.monotonic() + METER_REFRESH_INTERVAL
            elif command == "up":
                navigation.move_selection(-1)
                refresh_view()
            elif command == "down":
                navigation.move_selection(1)
                refresh_view()
            elif command == "p":
                action = "previous"
                break
            elif command == "n":
                action = "next"
                break
            elif command == "r":
                repeat_current = not repeat_current
                refresh_view()
            elif command == "s":
                navigation.toggle_shuffle()
                refresh_view()
            elif command == "a":
                download_jobs.put((track["url"], track["title"], "audio"))
                print(f"\nQueued audio download: {track['title']}")
            elif command == "v":
                download_jobs.put((track["url"], track["title"], "video"))
                print(f"\nQueued video download: {track['title']}")
            elif command == "q":
                process.terminate()
                process.wait()
                print("\nGoodbye!")
                sys.exit(0)

        # Stop mpv after a manual skip, and report unexpected player failures.
        if process.poll() is None:
            process.terminate()
            process.wait()
        elif action is None and process.returncode != 0:
            error_reader.join(timeout=1)
            code = process.returncode & 0xFFFFFFFF
            print(f"\nmpv exited unexpectedly with code 0x{code:08X}.")
            if args.show_stream_url_on_error:
                print("Full media stream URL (temporary; do not share):")
                print(f"   {stream_url}")
            if mpv_errors:
                print("mpv diagnostics (URLs and credentials are hidden):")
                for line in mpv_errors:
                    line = re.sub(r"https?://\S+", "[URL omitted]", line)
                    line = re.sub(
                        r"(?i)\b(authorization|cookie)\s*[:=]\s*\S+",
                        r"\1: [redacted]",
                        line,
                    )
                    print(f"   {line}")
            if code == 0xC000001D:
                print(
                    "Windows reported an unsupported CPU instruction. "
                    "The current mpv build fails even with local files."
                )
                print(
                    "Download a standard Windows x64 mpv build (avoid 64bit-v3 "
                    "or other newer-CPU variants):"
                )
                print_terminal_link(
                    "https://sourceforge.net/projects/mpv-player-windows/files/"
                    "64bit/mpv-x86_64-20261018-git-01e2533f31.7z/download"
                )
                print("Other operating systems:")
                print_terminal_link("https://mpv.io/installation/")
                print(
                    "Extract it beside player.py into mpv-portable so the path "
                    "is mpv-portable\\mpv.exe; keep the archive's DLLs beside it."
                )
                print(
                    "TubeQueue checks mpv-portable before versions found on PATH. "
                    "Run mpv-portable\\mpv.exe --version to verify it starts."
                )
            else:
                print("Check your mpv installation and its error messages.")
            sys.exit(1)

        clear_active_playback(process)

        # Move the playlist position based on the key pressed or repeat setting.
        if action == "previous":
            navigation.previous()
        elif action == "next":
            navigation.next()
        elif action == "select":
            navigation.select()
        elif not repeat_current:
            navigation.next()

    print("\nPlaylist finished.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        stop_active_playback()
        print("\nGoodbye!")
