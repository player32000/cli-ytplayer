"""Small terminal view showing the current track and nearby playlist items."""

import math
import shutil
import sys
import textwrap

from terminal_style import style
from windows_console import clear_console_screen


def display_playlist(
    tracks: list[dict],
    index: int,
    selected_index: int,
    status: str,
    show_help: bool,
    redraw: bool,
    list_label: str = "Playlist",
    use_color: bool = False,
    elapsed_seconds: float = 0,
    duration_seconds: float | None = None,
    audio_level_db: float | None = None,
    show_meter: bool = False,
    meter_available: bool = True,
) -> None:
    """Show up to six nearby tracks and mark the playing and selected items."""
    if redraw:
        if not clear_console_screen():
            sys.stdout.write("\033[2J\033[H")

    terminal_size = shutil.get_terminal_size((100, 20))
    columns = max(1, terminal_size.columns)
    help_lines = _help_lines(show_help, meter_available)
    if terminal_size.lines < 14:
        help_lines = help_lines[:2]
    if terminal_size.lines < 10:
        help_lines = []
    available_track_rows = terminal_size.lines - 5 - len(help_lines) - int(show_meter)
    visible_track_count = min(6, max(0, available_track_rows), len(tracks))
    start = min(
        max(0, selected_index - visible_track_count // 2),
        max(0, len(tracks) - visible_track_count),
    )
    end = min(len(tracks), start + visible_track_count)
    header = f"{list_label}: tracks {start + 1}-{end} of {len(tracks)}"
    print(style(_fit_line(header, columns), "title", use_color))
    current_title = _shorten_text(
        tracks[index]["title"],
        width=max(1, columns - len(f"Now playing: [{index + 1}/{len(tracks)}] ")),
    )
    now_playing = _fit_line(
        f"Now playing: [{index + 1}/{len(tracks)}] {current_title}",
        columns,
    )
    print(style(now_playing, "current", use_color))
    elapsed = _format_time(elapsed_seconds)
    duration = _format_time(duration_seconds) if duration_seconds is not None else "--:--"
    print(style(_fit_line(f"Time: {elapsed} / {duration}", columns), "muted", use_color))
    for track_index in range(start, end):
        if track_index == selected_index and track_index == index:
            marker = "*>"
        elif track_index == selected_index:
            marker = " >"
        elif track_index == index:
            marker = " *"
        else:
            marker = "  "
        prefix = f"{marker} [{track_index + 1:>4}/{len(tracks)}] "
        title = _shorten_text(
            tracks[track_index]["title"],
            width=max(1, columns - len(prefix)),
        )
        line = _fit_line(f"{prefix}{title}", columns)
        if track_index == selected_index:
            line = style(line, "selected", use_color)
        elif track_index == index:
            line = style(line, "current", use_color)
        print(line)
    if visible_track_count and terminal_size.lines >= 7:
        print()
    print(style(_fit_line(status, columns), "status", use_color))
    for line in help_lines:
        print(_fit_line(line, columns))
    if show_meter:
        sys.stdout.write(_format_audio_meter(audio_level_db, use_color, columns))
    sys.stdout.flush()


def update_audio_meter_line(
    level_db: float | None,
    use_color: bool,
) -> None:
    """Replace the meter on the current line without adding terminal output rows."""
    columns = max(1, shutil.get_terminal_size((100, 20)).columns)
    meter = _format_audio_meter(level_db, use_color, columns)
    sys.stdout.write(f"\r\033[2K{meter}")
    sys.stdout.flush()


def update_playback_time_line(elapsed_seconds: float, duration_seconds: float | None) -> None:
    """Update the time row in place without redrawing the entire playlist."""
    elapsed = _format_time(elapsed_seconds)
    duration = _format_time(duration_seconds) if duration_seconds is not None else "--:--"
    sys.stdout.write(f"\033[s\033[3;1H\033[2KTime: {elapsed} / {duration}\033[u")
    sys.stdout.flush()


def _format_time(seconds: float) -> str:
    if not math.isfinite(seconds):
        return "--:--"
    total_seconds = max(0, int(seconds))
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes:02}:{seconds:02}"


def _format_audio_meter(
    level_db: float | None,
    use_color: bool,
    width: int | None = None,
) -> str:
    """Render an RMS meter sized to fit the current terminal width."""
    filled_glyph, empty_glyph = _meter_glyphs()
    columns = max(1, width or shutil.get_terminal_size((100, 20)).columns)
    if columns < 32:
        if level_db is None or math.isnan(level_db):
            return _fit_line("Audio RMS: waiting for signal", columns)
        return _fit_line(f"Audio RMS: {level_db:6.1f} dBFS", columns)
    bar_length = min(30, columns - 25)
    if level_db is None or math.isnan(level_db):
        return f"Audio RMS: [{empty_glyph * bar_length}] waiting"
    bounded_level = min(0.0, max(-60.0, level_db))
    filled = round((bounded_level + 60.0) / 60.0 * bar_length)
    segments = (
        ("success", round(bar_length * 0.7)),
        ("warning", round(bar_length * 0.2)),
        ("danger", bar_length - round(bar_length * 0.7) - round(bar_length * 0.2)),
    )
    bar_parts = []
    segment_start = 0
    for color_name, segment_length in segments:
        segment_end = segment_start + segment_length
        lit_length = min(segment_length, max(0, filled - segment_start))
        lit = filled_glyph * lit_length
        unlit = empty_glyph * (segment_length - lit_length)
        if use_color:
            lit = style(lit, color_name, True)
            unlit = style(unlit, "muted", True)
        bar_parts.append(lit + unlit)
        segment_start = segment_end
    return f"Audio RMS: [{''.join(bar_parts)}] {level_db:6.1f} dBFS"


def _help_lines(show_help: bool, meter_available: bool) -> list[str]:
    if not show_help:
        return []
    return [
        "Up/Down = select | Enter = play selected | n = next | p = previous",
        "r = repeat | s = shuffle | a = queue MP3 | v = queue video | q = quit | h = hide help",
        (
            "m = toggle real audio RMS meter"
            if meter_available
            else "Audio meter unavailable in this mpv build"
        ),
        "--no-color = disable colored terminal output",
        "Single-track downloads run in the background and are processed one at a time.",
    ]


def _fit_line(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    if width <= 3:
        return text[:width]
    return f"{text[:width - 3]}..."


def _shorten_text(text: str, width: int) -> str:
    if width <= 3:
        return _fit_line(text, width)
    return textwrap.shorten(text, width=width, placeholder="...")


def _meter_glyphs() -> tuple[str, str]:
    """Use block characters where encodable, with an ASCII-safe fallback."""
    encoding = getattr(sys.stdout, "encoding", None)
    if encoding:
        try:
            "█░".encode(encoding)
        except (LookupError, UnicodeEncodeError):
            return "#", "."
    return "█", "░"
