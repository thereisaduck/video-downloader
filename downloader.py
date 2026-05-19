#!/usr/bin/env python3
"""
Multi-Platform Social Media Downloader (YouTube, Twitter, TikTok, Instagram, Threads)
Based on yt-dlp + ffmpeg.
Cookies via cookies.txt (Netscape format).

Version 2.1.0: Added Threads.net + post-download rename
"""

import sys
from pathlib import Path

from downloader import (
    YouTubeDownloader,
    TwitterDownloader,
    TikTokDownloader,
    InstagramDownloader,
    ThreadsDownloader,
    detect_platform_from_url,
    ensure_cookies,
    save_cookies_from_user_input,
    save_cookies_from_raw_string,
    rename_output_folder,
    check_ffmpeg,
    DOWNLOAD_DIR,
)


# ============================================================
#  Platform Router
# ============================================================

def _ask_rename(current_dir: str) -> str:
    """After download, optionally rename folder/files. Returns (possibly new) dir path."""
    new_dir = rename_output_folder(current_dir)
    return new_dir if new_dir else current_dir


# ---------- YouTube ----------

def download_youtube(url: str):
    downloader = YouTubeDownloader()

    print("\n" + "=" * 50)
    print("  YouTube Download")
    print("=" * 50)

    downloader.print_formats(url)

    print("Download mode:")
    print("  [1] Video+Audio+Subtitles (pick)")
    print("  [2] Video+Audio (no subs)")
    print("  [3] Video only (no audio)")
    print("  [4] Audio only (MP3)")
    print("  [5] Custom format ID")
    print("  [6] Subtitles only (pick)")
    print("  [q] Quit")

    choice = input("\n> Pick [1-6]: ").strip()
    format_map = {"1": "best", "2": "best_nosubs", "3": "video", "4": "audio"}
    format_choice = format_map.get(choice)

    if choice == "5":
        format_choice = input("Format ID (e.g. 137+140 or 22): ").strip()
        if not format_choice:
            print("No format ID")
            return
    elif choice == "6":
        downloader.download_subtitles(url)
        return
    elif choice.lower() == "q":
        print("Quit")
        return
    elif format_choice is None:
        print("Invalid option")
        return

    # Track output dir for rename prompt
    safe_title = downloader._sanitize_filename(
        downloader.get_video_info(url)["title"]
    )
    expected_dir = Path(DOWNLOAD_DIR) / safe_title

    downloader.download(url, {
        "format_choice": format_choice,
        "skip_subs": (format_choice == "best_nosubs"),
    })

    # Find the actual output directory (matches title with sanitization)
    actual_dir = _find_output_dir(expected_dir)
    if actual_dir:
        _ask_rename(str(actual_dir))


def _find_output_dir(expected: Path) -> Path | None:
    """Find the actual output directory (may differ slightly from expected)."""
    if expected.exists():
        return expected
    # Search for closest match
    parent = expected.parent
    name_lower = expected.name.lower()
    for d in sorted(parent.iterdir(), reverse=True):
        if d.is_dir() and d.name.lower().startswith(name_lower[:20]):
            return d
    return None


# ---------- Twitter/X ----------

def download_twitter(url: str):
    downloader = TwitterDownloader()

    print("\n" + "=" * 50)
    print("  Twitter/X Download")
    print("=" * 50)

    try:
        info = downloader.get_video_info(url)
    except Exception as e:
        downloader.print_error(str(e))
        return

    print(f"\nAuthor: {info['uploader']}")
    print(f"Content: {info['description'][:100]}...")
    print()

    # Thread selection
    if info.get("is_thread"):
        print("Thread detected:")
        print("  [1] Download single post")
        print("  [2] Download entire thread")
        choice = input("\n> Pick [1/2]: ").strip()
        thread_mode = "thread" if choice == "2" else "single"
    else:
        thread_mode = "single"

    downloader.download(url, {
        "thread_mode": thread_mode,
    })

    # Find output dir for rename prompt
    uploader = downloader._sanitize_filename(info["uploader"])
    title = downloader._sanitize_filename(info["title"][:50])
    expected_dir = Path(DOWNLOAD_DIR) / f"{uploader}_{title}"
    actual_dir = _find_output_dir(expected_dir)
    if actual_dir:
        _ask_rename(str(actual_dir))


# ---------- TikTok ----------

def download_tiktok(url: str):
    downloader = TikTokDownloader()

    print("\n" + "=" * 50)
    print("  TikTok Download")
    print("=" * 50)

    try:
        info = downloader.get_video_info(url)
    except Exception as e:
        downloader.print_error(str(e))
        return

    print(f"\nAuthor: {info['uploader']}")
    print(f"Title: {info['title']}")
    print()

    print("Download options:")
    print("  [1] Download video (with audio)")
    print("  [2] Extract audio only (MP3)")
    choice = input("\n> Pick [1/2]: ").strip()
    extract_audio_only = choice == "2"

    downloader.download(url, {
        "include_audio": True,
        "extract_audio_only": extract_audio_only,
    })

    # Find output dir for rename prompt
    uploader = downloader._sanitize_filename(info["uploader"])
    title = downloader._sanitize_filename(info["title"][:50])
    expected_dir = Path(DOWNLOAD_DIR) / f"{uploader}_{title}"
    actual_dir = _find_output_dir(expected_dir)
    if actual_dir:
        _ask_rename(str(actual_dir))


# ---------- Instagram ----------

def download_instagram(url: str):
    downloader = InstagramDownloader()

    print("\n" + "=" * 50)
    print("  Instagram Download")
    print("=" * 50)

    try:
        info = downloader.get_video_info(url)
    except Exception as e:
        downloader.print_error(str(e))
        return

    print(f"\nUser: {info['uploader']}")
    print(f"Title: {info['title']}")
    if info.get("is_carousel"):
        print(f"Carousel: {info['media_count']} media items")
    print()

    downloader.download(url, {
        "extract_carousel": True,
    })

    # Find output dir for rename prompt
    uploader = downloader._sanitize_filename(info["uploader"])
    title = downloader._sanitize_filename(info["title"][:50])
    expected_dir = Path(DOWNLOAD_DIR) / f"{uploader}_{title}"
    actual_dir = _find_output_dir(expected_dir)
    if actual_dir:
        _ask_rename(str(actual_dir))


# ---------- Threads ----------

def download_threads(url: str):
    downloader = ThreadsDownloader()

    print("\n" + "=" * 50)
    print("  Threads Download")
    print("=" * 50)

    try:
        info = downloader.get_video_info(url)
    except Exception as e:
        downloader.print_error(str(e))
        return

    print(f"\nAuthor: {info['uploader']}")
    print(f"Caption: {info['description'][:100]}...")
    print()

    downloader.download(url, {})

    # Find output dir for rename prompt
    uploader = downloader._sanitize_filename(info["uploader"])
    title = downloader._sanitize_filename(info["title"][:50])
    expected_dir = Path(DOWNLOAD_DIR) / f"{uploader}_{title}"
    actual_dir = _find_output_dir(expected_dir)
    if actual_dir:
        _ask_rename(str(actual_dir))


# ============================================================
#  Main
# ============================================================

def main():
    print("=" * 50)
    print("  Multi-Platform Video Downloader v2.1")
    print("=" * 50)
    print("  YouTube | Twitter/X | TikTok | Instagram | Threads")
    print("=" * 50)

    # Special modes
    if len(sys.argv) > 1:
        if sys.argv[1] == "--save-cookie":
            save_cookies_from_raw_string()
            return
        elif sys.argv[1] == "--set-cookie":
            save_cookies_from_user_input()
            return

    # Check ffmpeg
    if not check_ffmpeg():
        print("ERROR: ffmpeg not found")
        print("Make sure ffmpeg is at: ffmpeg-*/bin/")
        sys.exit(1)

    # Get URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("\nEnter URL: ").strip()

    if not url:
        print("No URL entered")
        sys.exit(1)

    # Platform detection and selection
    auto_platform = detect_platform_from_url(url)

    if auto_platform != "unknown":
        print(f"\nAuto-detected: {auto_platform.upper()}")
        choice = input(
            "Press Enter to continue, or type platform "
            "(youtube/twitter/tiktok/instagram/threads): "
        ).strip().lower()
        platform = choice if choice else auto_platform
    else:
        print("\nCannot auto-detect platform")
        print("\nPick a platform:")
        print("  [1] YouTube")
        print("  [2] Twitter/X")
        print("  [3] TikTok")
        print("  [4] Instagram")
        print("  [5] Threads")
        print("  [q] Quit")

        choice = input("\n> Pick [1-5]: ").strip()
        platform_map = {
            "1": "youtube",
            "2": "twitter",
            "3": "tiktok",
            "4": "instagram",
            "5": "threads",
        }
        platform = platform_map.get(choice)

        if choice.lower() == "q":
            print("Quit")
            return
        elif platform is None:
            print("Invalid option")
            return

    # Route to platform
    download_funcs = {
        "youtube": download_youtube,
        "twitter": download_twitter,
        "tiktok": download_tiktok,
        "instagram": download_instagram,
        "threads": download_threads,
    }

    # Ensure cookies (only prompts for YouTube)
    ensure_cookies(for_platform=platform)

    download_func = download_funcs.get(platform)
    if download_func:
        try:
            download_func(url)
        except KeyboardInterrupt:
            print("\n\nUser interrupted")
        except Exception as e:
            print(f"\nError: {e}")
    else:
        print(f"Unsupported platform: {platform}")


if __name__ == "__main__":
    main()
