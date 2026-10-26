#!/usr/bin/env python3
"""
download_playlist.py

Download tracks or videos from a YouTube liked playlist or a custom playlist.
Works on Windows (cmd/PowerShell), Linux, and macOS.

Requirements:
    python -m pip install -U "yt-dlp[default]"
    Node.js 22+ or Deno 2.3+ on PATH for YouTube's JavaScript challenge
    ffmpeg on PATH for audio extraction and conversion

Sources:
    lm     = YouTube Music liked tracks (default)
    ll     = regular YouTube liked videos
    custom = a playlist URL (requires --url)

Cookies are not discovered automatically. Pass a Netscape-format cookie file
with --cookies, or omit it to use the browser selected with --browser.

Progress is shared with player.py and stored in download_archive.txt to
preserve existing download history.
"""

import argparse
import shutil
import sys

try:
    import yt_dlp
    from yt_dlp.utils import sanitize_filename
except ImportError:
    print('yt-dlp is missing. Install it with: python -m pip install -U "yt-dlp[default]"')
    sys.exit(1)


# These are the built-in playlists: "lm" is YouTube Music likes, and "ll"
# is regular YouTube likes. Each entry also sets the output folder and filename style.
FIXED_SOURCES = {
    "lm": {
        "url": "https://music.youtube.com/playlist?list=LM",
        "folder": "descargas_liked_music",
        "filename_template": "%(artist,uploader)s - %(title)s.%(ext)s",
    },
    "ll": {
        "url": "https://www.youtube.com/playlist?list=LL",
        "folder": "descargas_liked_videos",
        "filename_template": "%(uploader)s - %(title)s.%(ext)s",
    },
}

# yt-dlp stores completed video IDs here so later runs can skip them.
DOWNLOAD_ARCHIVE = "download_archive.txt"


def cookie_options(browser: str, cookie_file: str) -> dict:
    """Choose how yt-dlp signs in: use the cookie file, or the selected browser."""
    if cookie_file:
        return {"cookiefile": cookie_file}
    return {"cookiesfrombrowser": (browser,)}


def youtube_javascript_options() -> dict:
    """Set up the helper yt-dlp needs to read YouTube's available formats."""
    options = {"remote_components": ["ejs:github"]}
    if shutil.which("node"):
        options["js_runtimes"] = {"node": {}}
    return options


def get_playlist_title(url: str, browser: str, cookie_file: str) -> str:
    """Read playlist details without downloading tracks, mainly to get its title."""
    options = {"quiet": True, "extract_flat": True, "skip_download": True}
    options.update(youtube_javascript_options())
    options.update(cookie_options(browser, cookie_file))
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return info.get("title") or "playlist_without_name"


def get_source_config(source: str, playlist_url: str, browser: str, cookie_file: str) -> dict:
    """Choose the playlist URL, output folder, and filename style."""
    if source == "custom":
        if not playlist_url:
            raise ValueError("With --source custom, you must also provide --url <playlist_url>.")
        # Use the playlist's own title to make a safe and recognizable folder name.
        title = get_playlist_title(playlist_url, browser, cookie_file)
        folder = sanitize_filename(title, restricted=True)
        return {
            "url": playlist_url,
            "folder": f"descargas_{folder}",
            "filename_template": "%(artist,uploader)s - %(title)s.%(ext)s",
        }
    return FIXED_SOURCES[source]


def build_download_options(config: dict, mode: str, browser: str, cookie_file: str) -> dict:
    """Tell yt-dlp what to download, where to save it, and how to sign in."""
    options = {
        "download_archive": DOWNLOAD_ARCHIVE,
        "ignoreerrors": True,
        "outtmpl": f"{config['folder']}/{config['filename_template']}",
        "noplaylist": False,
    }
    options.update(youtube_javascript_options())
    options.update(cookie_options(browser, cookie_file))

    # Audio is converted to MP3; video is saved as an MP4 when possible.
    if mode == "audio":
        options["format"] = "bestaudio/best"
        options["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"},
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ]
        options["writethumbnail"] = True
    else:
        options["format"] = "bv*[height<=1080]+ba/best[height<=1080]"
        options["merge_output_format"] = "mp4"

    return options


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add the playlist and sign-in choices shared with the player."""
    # Spanish aliases keep older commands working; English names are preferred.
    parser.add_argument(
        "--source", "--origen",
        dest="source",
        choices=["lm", "ll", "custom"],
        default="lm",
        help="lm = YouTube Music, ll = regular YouTube, custom = a playlist URL (default: lm)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Playlist URL (required when --source custom is used)",
    )
    parser.add_argument(
        "--browser", "--navegador",
        dest="browser",
        default="chrome",
        help="Browser used for cookies, e.g. chrome, firefox, brave, edge (default: chrome)",
    )
    parser.add_argument(
        "--cookies",
        default=None,
        help="Path to a Netscape-format cookies.txt file; overrides --browser",
    )


def main() -> None:
    # Read the user's choices from the command line.
    parser = argparse.ArgumentParser(description="Download a YouTube liked playlist or a custom playlist.")
    add_common_arguments(parser)
    parser.add_argument(
        "--mode", "--modo",
        dest="mode",
        choices=["audio", "video"],
        default="audio",
        help="Download as audio (MP3) or video (MP4) (default: audio)",
    )
    args = parser.parse_args()

    # Turn the selected source into its URL and destination settings.
    try:
        config = get_source_config(args.source, args.url, args.browser, args.cookies)
    except ValueError as error:
        parser.error(str(error))

    print(f"Source: {args.source} ({config['url']})")
    print(f"Cookie file: {args.cookies}" if args.cookies else f"Browser cookies: {args.browser}")
    print(f"Download mode: {args.mode}")
    print(f"Output folder: {config['folder']}")
    print()

    # Download every item in the playlist; yt-dlp updates the shared archive.
    options = build_download_options(config, args.mode, args.browser, args.cookies)
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([config["url"]])

    print("\nDone. Check the output folder.")


if __name__ == "__main__":
    main()
