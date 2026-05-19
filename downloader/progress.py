"""
Progress tracking and logging utilities
"""


def progress_hook(d):
    """
    Generic progress callback for download operations.
    Compatible with yt-dlp's progress_hooks.
    """
    if d["status"] == "downloading":
        percent = d.get("_percent_str", "N/A").strip()
        speed = d.get("_speed_str", "N/A").strip()
        eta = d.get("_eta_str", "N/A").strip()
        print(f"\rDownloading: {percent} | Speed: {speed} | ETA: {eta}", end="", flush=True)
    elif d["status"] == "finished":
        print(f"\rDownload complete, processing...{' ' * 30}")
