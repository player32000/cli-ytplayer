# TubeQueue

[English](README.md) | [Español](es/README.md)

TubeQueue is a command-line tool to search, stream, and download individual
videos and playlists from YouTube and YouTube Music. The root-level scripts are
the single, English-language source of truth.

## Features

- Streams playlists one track at a time without downloading them in advance,
  in audio-only or video-with-audio mode.
- Goes to the previous or next track and repeats the current track.
- Downloads the current track as MP3 audio or video from the player.
- Downloads entire playlists as audio or video.
- Supports YouTube Music liked tracks (`lm`), YouTube liked videos (`ll`), and
  custom playlists (`custom`).
- Shares download progress between the player and downloader.

## Install on Windows

TubeQueue requires Python and external media tools; the release does not bundle
those programs. Install Python 3.10 or later, then install the Python
dependency from this folder:

```powershell
python -m pip install -r requirements.txt
```

Playback requires `mpv`. MP3 conversion requires `ffmpeg` on `PATH`. YouTube
access through yt-dlp also requires Node.js 22 or later, or Deno 2.3 or later.
See [Requirements](#requirements) for details.

To run `tubequeue` from any Command Prompt directory:

1. Keep this folder in a permanent location, or download and extract the
   project to one (for example, `%LOCALAPPDATA%\Programs\TubeQueue`).
2. Add that folder to your **user Path** through Windows **Edit environment
   variables for your account**. Add the folder itself, not the `.cmd` file.
3. Close and reopen Command Prompt, then run `tubequeue` or
   `tubequeue --help`.

The `tubequeue.cmd` launcher starts the interactive player and forwards any
arguments to `player.py`. When the program exits, the launcher waits for a key
press before closing so messages remain visible. This pause also occurs when
launched from an already-open Command Prompt. Downloads and progress archives
are written relative to the current working directory. Python and the external
tools above must be installed separately.

For source-code contributions, clone the repository or download its source
archive. A packaged Windows release can be distributed through GitHub Releases
when available.

## Requirements

- **Python 3.10 or later** runs TubeQueue. The Windows `tubequeue.cmd` launcher
  checks for it and explains how to install it if it is missing.
- **yt-dlp** searches YouTube, reads playlist entries, streams media, and
  downloads videos/audio. Install it with its default components:

  ```powershell
  python -m pip install -r requirements.txt
  ```

- **Node.js 22 or later, or Deno 2.3 or later** lets yt-dlp solve YouTube's
  JavaScript challenge and discover playable/downloadable formats. Either one
  is sufficient.
- **mpv**, compatible with your CPU, plays the audio/video stream. It is
  required for playback but not for playlist downloads.
- **FFmpeg** converts downloaded audio to MP3 and merges separate audio/video
  streams. It is required for downloads and optional during playback.

Before contacting YouTube, TubeQueue checks for the JavaScript runtime and,
when relevant, FFmpeg or mpv. It prints the missing component's purpose and
installation guidance. The Python launcher reports if Python 3.10+ is missing.

On Windows, `player.py` checks for `mpv.exe` in `mpv-portable` next to the
script, then on `PATH`, and then in standard installation locations. This
project does not bundle mpv. For a Windows x64 build, see the
[mpv Windows builds on SourceForge](https://sourceforge.net/projects/mpv-player-windows/files/64bit/mpv-x86_64-20261018-git-01e2533f31.7z/download).
For installation options on Windows, macOS, and Linux, see the official
[mpv installation guide](https://mpv.io/installation/).
If mpv exits with `0xC000001D` or Windows reports an unsupported CPU
instruction, try a standard x86-64 build and avoid variants optimized for
newer CPUs (such as `64bit-v3`). To make TubeQueue use a specific portable
build, extract the archive so `mpv.exe` and its DLLs are directly inside an
`mpv-portable` folder next to `player.py`, for example:

```
TubeQueue\
  player.py
  mpv-portable\
    mpv.exe
    ...
```

Keep the DLLs and other files from the archive together with `mpv.exe`. The
bundled-folder location is checked before mpv installations on `PATH`.

## Cookies and account access

For private playlists such as liked tracks, pass valid cookies exported in
Netscape format using `--cookies`. Cookie files are not detected automatically.
If `--cookies` is omitted, yt-dlp tries the browser selected with `--browser`
(Chrome by default).
For a public playlist without browser cookies, use `--browser none`.

Cookies are account credentials: **never share them or upload them to GitHub**.
The `.gitignore` excludes cookie files, downloaded media, progress data, Python
caches, and the optional local `mpv-portable` folder. Always review what you
are about to publish.

Replace `PATH\TO\cookies.txt` in the examples with the path to your own file.

## Player

Run `python player.py` from the project folder without arguments to open the
interactive setup. The first option is **Quick YouTube search (play audio)**:
enter a query and go directly to the results without choosing a source, playback
mode, or cookies. For other tasks, choose to play a list, download the full list
as MP3, or download it as video. For playback, choose audio-only or video with
audio; video opens in an mpv window, not inside the terminal. Then choose a public
playlist and paste its URL, search YouTube, or choose a private playlist/liked
items. Search shows up to 20 results and uses the same playlist navigation
controls. Bulk download applies to the selected playlist or all 20 search
results. For public playlists and searches, you can continue without account
cookies or choose an existing browser session or a cookie file.
Private playlists require account access: choose a browser where you are
already signed in, or choose the cookie-file option and enter the file path.
Menus refresh in place in an interactive terminal. Choose the displayed `Back`
option or type `b` at a text prompt to return to the previous menu.
Menu choices can be selected with the up/down arrows and Enter; numbered
selection remains available, and text prompts accept `b` to go back.

If browser access does not work, start the player again and choose the
`cookies.txt` option. The assistant guides you to sign in through your browser,
export cookies for `youtube.com` (and `music.youtube.com` for YouTube Music) in
Netscape format with a trusted exporter, then enter the full file path. Review
any export tool's permissions first. Do not share or upload the exported file:
it grants access to your account.
The assistant remembers only the file path in your local user settings (not the
cookie contents) and offers to reuse it next time. If access later fails, the
session may have expired; sign in again and export a fresh file.
On Windows, that setting is stored under `%LOCALAPPDATA%\YouTubePlaylistCLI`;
on macOS and Linux, it is stored under `~/.config/youtube-playlist-cli`.

You can still use command-line options directly:

```powershell
# YouTube Music liked tracks
python player.py --source lm --cookies "PATH\TO\cookies.txt"

# YouTube liked videos
python player.py --source ll --cookies "PATH\TO\cookies.txt"

# Custom playlist
python player.py --source custom --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" --cookies "PATH\TO\cookies.txt"

# Search YouTube (use --browser none to skip browser cookies)
python player.py --search "search terms" --browser none

# Download the full custom playlist as MP3 (use --mode video for video)
python player.py --source custom --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" --download-playlist --mode audio --cookies "PATH\TO\cookies.txt"

# Download the first 20 results of a search as MP3
python player.py --search "search terms" --download-playlist --browser none

# Play a playlist with video in an mpv window
python player.py --source custom --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" --mode video --cookies "PATH\TO\cookies.txt"
```

The command-line default is `--mode audio`; use `--mode video` to show video
with its audio during playback, or to choose video format for `--download-playlist`.
Terminal text is colored automatically when supported; use `--no-color` to
disable it. The player displays elapsed and total track time. The live ASCII
RMS level meter is shown by default; press `h` to show the playback help, then
`m` to hide or show it. Use `--no-meter` to start with it hidden.
The meter reads real audio levels from mpv's FFmpeg audio filters and reports
RMS in dBFS; green marks lower levels, yellow medium levels, and red higher
levels. It uses block characters when supported (otherwise ASCII) and updates
in place up to 40 times per second without redrawing the playlist; the rest of
the player view refreshes once per second to avoid flicker. It is not a
measurement of speaker volume.

Use the up/down arrow keys to select a track and press `Enter` to play it.
The view shows at most six tracks and scrolls as you move through the playlist;
`*` marks the playing track and `>` marks the selected track. Controls are
hidden by default; press `h` to show or hide the help. Press `n` to go to the
next track, `p` to go to the previous track, `r` to toggle repeat, `s` to
toggle shuffle, `a` to download the current audio, `v` to download the current
video, and `q` to quit. Shuffle plays every track once in a randomized order
before starting another randomized cycle. Controls work during playback and
while a track is loading. Windows uses the helpers in `windows_console.py`;
macOS and Linux use Python's terminal input.
Single-track downloads run in the background. You can queue more than one while
playback continues; the player processes those downloads one at a time to avoid
collisions. Full-list downloads are a separate startup operation and show
yt-dlp's batch progress.

These controls also work while the player is preparing a track, so you can
skip a slow-to-load item without waiting for its audio stream to finish loading.
In an interactive terminal, the playlist view refreshes in place instead of
adding a new view for every track.

If mpv exits unexpectedly, the player shows its diagnostic messages with URLs
and credential values hidden. To print the full, temporary media stream URL
when a failure occurs, run the player with `--show-stream-url-on-error`. Do not
share that URL; it may contain temporary access parameters.

Playlist items that YouTube reports as unavailable are skipped automatically.

## Playlist downloader

```powershell
# YouTube Music liked tracks as MP3
python download_playlist.py --source lm --mode audio --cookies "PATH\TO\cookies.txt"

# YouTube liked videos
python download_playlist.py --source ll --mode video --cookies "PATH\TO\cookies.txt"

# Custom playlist as MP3
python download_playlist.py --source custom --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" --mode audio --cookies "PATH\TO\cookies.txt"
```

The `lm` and `ll` sources download all available liked items in bulk. Use
`--source custom --url "PLAYLIST_URL"` to download a different playlist in
bulk. English options (`--source`, `--browser`, `--mode`) are recommended;
former Spanish aliases (`--origen`, `--navegador`, `--modo`) remain supported.

Downloads go into the existing `descargas_*` folders. Audio and video progress
are tracked separately in `download_archive_audio.txt` and
`download_archive_video.txt`, so downloading one format does not block the
other. On first use, each archive is initialized from the existing
`download_archive.txt` when that legacy file is present.

## Source files

- `player.py`: playlist player and current-track downloader.
- `interactive_setup.py`: startup menus for task, source, and account access.
- `console_input.py`: shared immediate keyboard input for startup menus and
  playback controls.
- `download_manager.py`: individual-track download queue and bulk-download
  execution.
- `terminal_style.py`: ANSI color capability detection and text styling.
- `player_settings.py`: stores the local cookie-file path, never cookie contents.
- `playlist_navigation.py`: selected-track, playback-history, and shuffle
  navigation.
- `playlist_view.py`: compact view of the current track and nearby playlist
  items, with selection and scrolling.
- `windows_console.py`: Windows console-mode helpers for screen updates and
  selection handling.
- `download_playlist.py`: source configuration, shared yt-dlp options, and the
  standalone bulk playlist downloader.
- `LICENSE`: MIT License.
- [`Spanish README`](es/README.md): translated documentation with a link back
  to this English README.

## License

This project is licensed under the [MIT License](LICENSE). You may use, modify,
and redistribute it, including in commercial projects, provided the copyright
and license notices are kept. The software is provided without warranty.
