# YouTube Playlist CLI

[English](README.md) | [Español](es/README.md)

A Python command-line player and downloader for YouTube and YouTube Music
playlists. The root-level scripts are the single, English-language source of
truth.

## Features

- Streams playlists one track at a time without downloading them in advance.
- Goes to the previous or next track and repeats the current track.
- Downloads the current track as MP3 audio or video from the player.
- Downloads entire playlists as audio or video.
- Supports YouTube Music liked tracks (`lm`), YouTube liked videos (`ll`), and
  custom playlists (`custom`).
- Shares download progress between the player and downloader.

## Requirements

- Python 3.10 or later.
- `yt-dlp` with its EJS components:

  ```powershell
  python -m pip install -U "yt-dlp[default]"
  ```

- A JavaScript runtime for YouTube's challenge: Node.js 22 or later, or Deno
  2.3 or later. Node.js is not mandatory; the program prefers Node.js when
  available, and yt-dlp can use Deno otherwise.
- An `mpv` build compatible with your CPU, required by `player.py`.
- `ffmpeg` on `PATH` for MP3 audio conversion.

On Windows, `player.py` checks for `mpv.exe` in `mpv-portable` next to the
script, then on `PATH`, and then in standard installation locations. This
project does not bundle mpv. Download a trusted build compatible with your
processor. If mpv exits with `0xC000001D`, try a standard x86-64 build instead
of one optimized for newer CPUs (such as `64bit-v3`).

## Cookies and account access

For private playlists such as liked tracks, pass valid cookies exported in
Netscape format using `--cookies`. Cookie files are not detected automatically.
If `--cookies` is omitted, yt-dlp tries the browser selected with `--browser`
(Chrome by default).

Cookies are account credentials: **never share them or upload them to GitHub**.
The `.gitignore` excludes cookie files, downloaded media, progress data, Python
caches, and the optional local `mpv-portable` folder. Always review what you
are about to publish.

Replace `PATH\TO\cookies.txt` in the examples with the path to your own file.

## Player

Run from the project folder:

```powershell
# YouTube Music liked tracks
python player.py --source lm --cookies "PATH\TO\cookies.txt"

# YouTube liked videos
python player.py --source ll --cookies "PATH\TO\cookies.txt"

# Custom playlist
python player.py --source custom --url "https://www.youtube.com/playlist?list=PLAYLIST_ID" --cookies "PATH\TO\cookies.txt"
```

On Windows, press controls directly without Enter: `Enter` goes to the next
track, `p` goes to the previous one, `r` toggles repeat, `a` downloads the
current audio, `v` downloads the current video, and `q` quits. The Windows-only
key reader and CMD Quick Edit handling are in `windows_console.py`. On macOS and
Linux, enter the control and press Enter; these systems use Python's standard
input instead.

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

Downloads go into the existing `descargas_*` folders. The shared progress
archive is `download_archive.txt` and preserves the existing download history.

## Source files

- `player.py`: playlist player and current-track downloader.
- `windows_console.py`: Windows-only instant key input and console selection
  handling. Other operating systems use the standard Python input method.
- `download_playlist.py`: downloads all items in a liked or custom playlist.
- [`Spanish README`](es/README.md): translated documentation with a link back
  to this English README.
