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

On Windows, controls are read directly without Enter, and CMD Quick Edit is
disabled while the player runs to prevent clicks from pausing playback. The
Windows-specific console code is kept in windows_console.py.
"""

import argparse
import atexit
import os
import queue
import shutil
import subprocess
import sys
import threading

try:
    import yt_dlp
except ImportError:
    print('yt-dlp is missing. Install it with: python -m pip install -U "yt-dlp[default]"')
    sys.exit(1)

from download_playlist import (
    add_common_arguments,
    build_download_options,
    cookie_options,
    get_source_config,
    youtube_javascript_options,
)
from windows_console import disable_quick_edit, read_windows_controls


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
        })
    return tracks


def download_track(
    url: str,
    title: str,
    config: dict,
    mode: str,
    browser: str,
    cookie_file: str,
) -> None:
    """Download one track in the background so playback can continue."""
    print(f"\n   -> Downloading ({mode}): {title} ...")
    options = build_download_options(config, mode, browser, cookie_file)
    options["noplaylist"] = True
    options["quiet"] = True
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        print(f"   -> Done: {title}")
    except Exception as error:
        print(f"   -> Error downloading '{title}': {error}")


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


def get_audio_stream(url: str, browser: str, cookie_file: str) -> tuple[str, dict]:
    """Ask yt-dlp for a playable audio URL and the web headers mpv needs."""
    options = {
        "quiet": True,
        "noplaylist": True,
        "format": "bestaudio/best",
    }
    options.update(youtube_javascript_options())
    options.update(cookie_options(browser, cookie_file))
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return info["url"], info.get("http_headers", {})


def start_playback(url: str, mpv_executable: str, headers: dict) -> subprocess.Popen:
    """Start mpv with audio only; the media itself is not saved to disk."""
    command = [mpv_executable, "--no-video", "--input-terminal=no"]
    if headers:
        # Pass YouTube's request details to mpv so the stream can be opened.
        fields = []
        for name, value in headers.items():
            escaped_value = value.replace("\\", "\\\\").replace(",", "\\,")
            fields.append(f"{name}: {escaped_value}")
        command.append(f"--http-header-fields={','.join(fields)}")
    command.append(url)
    return subprocess.Popen(command, stdin=subprocess.DEVNULL)


def read_controls(commands: queue.Queue) -> None:
    """Read key presses in the background while the song is playing."""
    if sys.platform == "win32":
        read_windows_controls(commands)
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
    # Find mpv first; without it there is no program available to play audio.
    mpv_executable = find_mpv()
    if not mpv_executable:
        print("mpv was not found. Install it or add mpv to PATH.")
        print("(Windows: winget install --id shinchiro.mpv --exact --source winget)")
        print("(macOS: brew install mpv | Linux: apt install mpv)")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Command-line playlist player with on-demand downloads.")
    add_common_arguments(parser)
    args = parser.parse_args()

    # "args" holds the user's command-line choices; "config" describes the playlist.
    try:
        config = get_source_config(args.source, args.url, args.browser, args.cookies)
    except ValueError as error:
        parser.error(str(error))

    print(f"Source: {args.source} ({config['url']})")
    print("Loading playlist...")
    # "tracks" is the ordered list of titles and URLs used during playback.
    tracks = list_tracks(config, args.browser, args.cookies)
    print(f"{len(tracks)} tracks found.\n")

    # On Windows, restore the console settings automatically when Python exits.
    restore_console = disable_quick_edit() if sys.platform == "win32" else None
    if restore_console:
        atexit.register(restore_console)

    # The reader thread collects keys while this main thread manages playback.
    commands = queue.Queue()
    threading.Thread(target=read_controls, args=(commands,), daemon=True).start()

    # "index" is the current position in the playlist; repeat_current controls auto-repeat.
    index = 0
    repeat_current = False
    while index < len(tracks):
        # "track" is the item at the current position. Resolve its stream before starting mpv.
        track = tracks[index]
        print(f"[{index + 1}/{len(tracks)}] {track['title']}")
        print("   Preparing audio...")
        try:
            stream_url, headers = get_audio_stream(track["url"], args.browser, args.cookies)
        except yt_dlp.utils.DownloadError as error:
            print(f"\nCould not prepare audio: {error}")
            print('Update yt-dlp and its components: python -m pip install -U "yt-dlp[default]"')
            print("You also need Deno 2.3.0+ or Node.js 22.0.0+ on PATH.")
            sys.exit(1)

        process = start_playback(stream_url, mpv_executable, headers)
        repeat_status = "on" if repeat_current else "off"
        print(
            "   Enter = next | p = previous | "
            f"r = repeat ({repeat_status}) | a = download MP3 | "
            "v = download video | q = quit"
        )
        if sys.platform == "win32":
            print("   Press a key directly, without Enter.")
        # "action" records a manual next/previous request; None means playback ended naturally.
        action = None

        # Check for key presses while mpv is still playing this track.
        while process.poll() is None:
            try:
                command = commands.get(timeout=0.2)
            except queue.Empty:
                continue

            if command == "":
                action = "next"
                break
            elif command == "p":
                action = "previous"
                break
            elif command == "r":
                repeat_current = not repeat_current
                status = "on" if repeat_current else "off"
                print(f"   Repeat current track: {status}")
            elif command == "a":
                threading.Thread(
                    target=download_track,
                    args=(track["url"], track["title"], config, "audio", args.browser, args.cookies),
                    daemon=True,
                ).start()
            elif command == "v":
                threading.Thread(
                    target=download_track,
                    args=(track["url"], track["title"], config, "video", args.browser, args.cookies),
                    daemon=True,
                ).start()
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
            code = process.returncode & 0xFFFFFFFF
            print(f"\nmpv exited unexpectedly with code 0x{code:08X}.")
            if code == 0xC000001D:
                print(
                    "Windows reported an unsupported CPU instruction. "
                    "The current mpv build fails even with local files."
                )
                print("Install an mpv build compatible with your processor and try again.")
            else:
                print("Check your mpv installation and its error messages.")
            sys.exit(1)

        # Move the playlist position based on the key pressed or repeat setting.
        if action == "previous":
            index = max(0, index - 1)
        elif action == "next":
            index += 1
        elif not repeat_current:
            index += 1

    print("\nPlaylist finished.")


if __name__ == "__main__":
    main()
