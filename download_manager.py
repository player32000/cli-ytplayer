"""Background single-track and foreground bulk download operations."""

import queue
import threading

import yt_dlp

from download_playlist import build_download_options


def download_track(
    url: str,
    title: str,
    config: dict,
    mode: str,
    browser: str,
    cookie_file: str,
) -> tuple[bool, str | None]:
    """Download one track without blocking playback."""
    print(f"\n   -> Downloading ({mode}): {title} ...")
    try:
        options = build_download_options(config, mode, browser, cookie_file)
        options["noplaylist"] = True
        options["quiet"] = True
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        print(f"   -> Done: {title}")
        return True, None
    except Exception as error:
        print(f"   -> Error downloading '{title}': {error}")
        return False, str(error)


def process_download_queue(
    jobs: queue.Queue,
    config: dict,
    browser: str,
    cookie_file: str,
    results: queue.Queue,
) -> None:
    """Process queued track downloads sequentially to avoid archive races."""
    while True:
        job = jobs.get()
        try:
            if job is None:
                return
            url, title, mode = job
            succeeded, error = download_track(
                url, title, config, mode, browser, cookie_file
            )
            results.put((title, mode, succeeded, error))
        finally:
            jobs.task_done()


def start_download_queue(
    config: dict,
    browser: str,
    cookie_file: str,
) -> tuple[queue.Queue, queue.Queue]:
    """Start the worker and return its job queue and completion notifications."""
    jobs = queue.Queue()
    results = queue.Queue()
    threading.Thread(
        target=process_download_queue,
        args=(jobs, config, browser, cookie_file, results),
        daemon=True,
    ).start()
    return jobs, results


def download_full_list(config: dict, mode: str, browser: str, cookie_file: str) -> None:
    """Download all items from the configured playlist or search results."""
    options = build_download_options(config, mode, browser, cookie_file)
    options["noplaylist"] = False
    print(f"Download mode: {'MP3 audio' if mode == 'audio' else 'video'}")
    print(f"Output folder: {config['folder']}")
    print("Starting bulk download...")
    with yt_dlp.YoutubeDL(options) as ydl:
        ydl.download([config["url"]])
    print("\nBulk download finished. Check the output folder.")
