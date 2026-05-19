"""
TikTok downloader with auto-quality selection.
Uses yt-dlp as the backend.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp not installed. Run: pip install yt-dlp")
    sys.exit(1)

from .base import BaseDownloader
from .utils import (
    check_ffmpeg,
    sanitize_filename,
    build_ydl_opts,
    DOWNLOAD_DIR,
)
from .progress import progress_hook


class TikTokDownloader(BaseDownloader):
    """
    TikTok video downloader with:
    - Auto-quality selection (best available)
    - Audio extraction option
    - Metadata extraction
    """

    def __init__(self):
        super().__init__("TikTok")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract TikTok video metadata.
        
        Returns:
            Dictionary with:
            - title, uploader, description
            - duration, views, likes
            - formats: available video formats
        """
        print("\nFetching TikTok video info...\n")

        try:
            with yt_dlp.YoutubeDL(build_ydl_opts({"quiet": True, "no_warnings": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise Exception(f"Failed to get video info: {e}")

        return {
            "title": info.get("title", "TikTok Video"),
            "uploader": info.get("uploader", "Unknown"),
            "description": info.get("description", ""),
            "duration": info.get("duration"),
            "duration_string": self._format_duration(info.get("duration")),
            "view_count": info.get("view_count"),
            "like_count": info.get("like_count"),
            "formats": info.get("formats", []),
            "_raw_info": info,
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List available video formats.
        """
        info = self.get_video_info(url)
        formats = info.get("formats", [])

        result = []
        shown = set()

        for fmt in formats:
            fmt_id = fmt.get("format_id", "?")
            if fmt_id in shown:
                continue
            shown.add(fmt_id)

            vcodec = fmt.get("vcodec", "h264")
            resolution = fmt.get("resolution", "best")

            result.append({
                "id": fmt_id,
                "type": "Video",
                "codec": vcodec,
                "resolution": resolution,
                "size": "N/A",
                "note": fmt.get("format_note", ""),
            })

        return result

    def download(
        self,
        url: str,
        options: Dict[str, Any] = None,
    ) -> bool:
        """
        Download TikTok video with auto-quality selection.
        
        Args:
            url: TikTok URL
            options: Dict with keys:
                - include_audio: bool (default: True, keep audio)
                - extract_audio_only: bool (default: False)
                - output_dir: str (optional)
                
        Returns:
            True if successful
        """
        if options is None:
            options = {}

        include_audio = options.get("include_audio", True)
        extract_audio_only = options.get("extract_audio_only", False)
        output_dir = options.get("output_dir", str(DOWNLOAD_DIR))

        if not check_ffmpeg():
            self.print_error("FFmpeg not found")
            return False

        # Get video info
        try:
            info = self.get_video_info(url)
        except Exception as e:
            self.print_error(str(e))
            return False

        # Prepare output dir
        uploader = sanitize_filename(info["uploader"])
        title = sanitize_filename(info["title"][:50])
        video_dir = Path(output_dir) / f"{uploader}_{title}"
        video_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nAuthor: {info['uploader']}")
        print(f"Title: {info['title']}")
        print(f"Duration: {info['duration_string']}")
        if info.get("view_count"):
            print(f"Views: {info['view_count']:,}")
        if info.get("like_count"):
            print(f"Likes: {info['like_count']:,}")
        print(f"Output: {video_dir}")

        if extract_audio_only:
            print("Mode: Extract audio only (MP3)")
        else:
            print("Mode: Download video (auto best quality)")
        print()

        # Build download options
        if extract_audio_only:
            format_str = "bestaudio"
            ydl_opts = build_ydl_opts({
                "format": format_str,
                "outtmpl": str(video_dir / "%(title)s.%(ext)s"),
                "progress_hooks": [progress_hook],
                "quiet": False,
                "no_warnings": False,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        else:
            # Video mode: best+audio
            if include_audio:
                format_str = "bestvideo+bestaudio/best"
            else:
                format_str = "bestvideo"

            ydl_opts = build_ydl_opts({
                "format": format_str,
                "outtmpl": str(video_dir / "%(title)s.%(ext)s"),
                "merge_output_format": "mp4",
                "progress_hooks": [progress_hook],
                "quiet": False,
                "no_warnings": False,
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Count downloaded files
            video_files = list(video_dir.glob("*"))
            self.print_success("Download complete!")
            for f in video_files:
                if f.is_file():
                    size_mb = f.stat().st_size / 1024 / 1024
                    print(f"  {f.name} ({size_mb:.1f} MB)")

            return True

        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    # ========== Helper methods ==========

    @staticmethod
    def _format_duration(seconds: Optional[int]) -> str:
        """
        Format duration in seconds to HH:MM:SS.
        """
        if seconds is None:
            return "N/A"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes}:{secs:02d}"
