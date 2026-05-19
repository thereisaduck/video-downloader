"""
Multi-platform video downloader package.

Supports: YouTube, Twitter/X, TikTok, Instagram, Threads

Usage:
    from downloader import YouTubeDownloader, detect_platform_from_url
    url = "https://www.youtube.com/watch?v=..."
    downloader = YouTubeDownloader()
    downloader.download(url, {"format_choice": "best"})
"""

from .base import BaseDownloader
from .progress import progress_hook
from .utils import (
    check_ffmpeg,
    has_cookies_file,
    ensure_cookies,
    save_cookies_from_user_input,
    save_cookies_from_raw_string,
    sanitize_filename,
    build_ydl_opts,
    detect_platform_from_url,
    rename_output_folder,
    WORKSPACE_DIR,
    DOWNLOAD_DIR,
    COOKIES_FILE,
)
from .youtube import YouTubeDownloader
from .twitter import TwitterDownloader
from .tiktok import TikTokDownloader
from .instagram import InstagramDownloader
from .threads import ThreadsDownloader

__version__ = "2.1.0"
__all__ = [
    "BaseDownloader",
    "YouTubeDownloader",
    "TwitterDownloader",
    "TikTokDownloader",
    "InstagramDownloader",
    "ThreadsDownloader",
    "progress_hook",
    "check_ffmpeg",
    "has_cookies_file",
    "ensure_cookies",
    "save_cookies_from_user_input",
    "save_cookies_from_raw_string",
    "sanitize_filename",
    "build_ydl_opts",
    "detect_platform_from_url",
    "rename_output_folder",
    "WORKSPACE_DIR",
    "DOWNLOAD_DIR",
    "COOKIES_FILE",
]
