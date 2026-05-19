"""
Threads.net downloader for videos and media posts.
Uses yt-dlp as the backend (native Threads support).
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp not installed, run: pip install yt-dlp")
    sys.exit(1)

from .base import BaseDownloader
from .utils import (
    check_ffmpeg,
    sanitize_filename,
    build_ydl_opts,
    DOWNLOAD_DIR,
)
from .progress import progress_hook


class ThreadsDownloader(BaseDownloader):
    """
    Threads.net post/video downloader.
    
    Features:
    - Download single Threads posts with media (video/images)
    - Metadata extraction (author, caption, timestamp)
    - Support for multi-image posts
    """

    def __init__(self):
        super().__init__("Threads")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract Threads post metadata.
        
        Returns:
            Dictionary with:
            - title, uploader, description
            - formats: available media formats
            - post_id: Threads post ID
            - is_thread: True if part of a conversation thread
        """
        print("\nSearching for Threads post info...\n")

        try:
            with yt_dlp.YoutubeDL(build_ydl_opts({"quiet": True, "no_warnings": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise Exception(f"Cannot get post info: {e}")

        uploader = info.get("uploader", "Unknown")
        description = info.get("description", "")
        title = info.get("title", f"Threads - {uploader}")

        return {
            "title": title,
            "uploader": uploader,
            "description": description,
            "timestamp": info.get("upload_date"),
            "formats": info.get("formats", []),
            "_raw_info": info,
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List available media formats (video, images).
        """
        info = self.get_video_info(url)
        formats = info.get("formats", [])

        result = []
        if not formats:
            result.append({
                "id": "default",
                "type": "Mixed Media",
                "codec": "auto",
                "resolution": "best",
                "size": "N/A",
                "note": "Auto-select best quality",
            })
        else:
            shown = set()
            for fmt in formats:
                fmt_id = fmt.get("format_id", "?")
                if fmt_id in shown:
                    continue
                shown.add(fmt_id)

                vcodec = fmt.get("vcodec", "none")
                fmt_type = "Video" if vcodec != "none" else "Image"
                codec = fmt.get("vcodec", fmt.get("acodec", "unknown"))

                result.append({
                    "id": fmt_id,
                    "type": fmt_type,
                    "codec": codec,
                    "resolution": fmt.get("resolution", "best"),
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
        Download Threads post media.
        
        Args:
            url: Threads post URL
            options: Dict with keys:
                - include_metadata: bool (default: False)
                - output_dir: str (optional)
                
        Returns:
            True if successful
        """
        if options is None:
            options = {}

        include_metadata = options.get("include_metadata", False)
        output_dir = options.get("output_dir", str(DOWNLOAD_DIR))

        if not check_ffmpeg():
            self.print_error("FFmpeg not found")
            return False

        # Get post info
        try:
            info = self.get_video_info(url)
        except Exception as e:
            self.print_error(str(e))
            return False

        # Prepare output directory
        uploader = sanitize_filename(info["uploader"])
        title = sanitize_filename(info["title"][:50])
        post_dir = Path(output_dir) / f"{uploader}_{title}"
        post_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nAuthor: {info['uploader']}")
        print(f"Caption: {info['description'][:100]}...")
        print(f"Output: {post_dir}")
        print()

        # Download — don't restrict format, let yt-dlp grab all media (images + video)
        temp_template = str(post_dir / "%(title)s_%(format_id)s.%(ext)s")

        ydl_opts = build_ydl_opts({
            "outtmpl": temp_template,
            "progress_hooks": [progress_hook],
            "quiet": False,
            "no_warnings": False,
        })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Rename all media files sequentially → _1, _2, _3 ...
            self._rename_media_sequential(post_dir, f"{uploader}_{title}")

            # Save metadata
            if include_metadata:
                self._save_metadata(post_dir, info)

            # List downloaded files
            media_files = [f for f in post_dir.iterdir() if f.is_file()]
            self.print_success("Download complete!")
            for f in media_files:
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"  {f.name} ({size_mb:.1f} MB)")

            return True

        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    # ========== Helpers ==========

    def _rename_media_sequential(self, post_dir: Path, base_name: str):
        """
        Rename all media files in the output directory sequentially:
        base_1.ext, base_2.ext, base_3.ext ...
        Skips .txt metadata files.
        """
        media_exts = {
            ".mp4", ".webm", ".mkv", ".mov",
            ".jpg", ".jpeg", ".png", ".gif", ".webp",
            ".mp3", ".aac", ".m4a", ".opus", ".ogg",
        }

        media_files = sorted([
            f for f in post_dir.iterdir()
            if f.is_file() and f.suffix.lower() in media_exts
        ])

        if len(media_files) <= 1:
            if media_files:
                ext = media_files[0].suffix
                new_name = f"{base_name}{ext}"
                new_path = post_dir / new_name
                try:
                    media_files[0].rename(new_path)
                    print(f"Renamed: {media_files[0].name} -> {new_name}")
                except Exception as e:
                    print(f"Rename skipped: {e}")
            return

        print(f"\nRenaming {len(media_files)} media files sequentially...")

        for idx, f in enumerate(media_files, 1):
            ext = f.suffix
            new_name = f"{base_name}_{idx:02d}{ext}"
            new_path = post_dir / new_name
            try:
                f.rename(new_path)
                print(f"  [{idx}] {f.name} -> {new_name}")
            except Exception as e:
                print(f"  [{idx}] Skip {f.name}: {e}")

    def _save_metadata(self, output_dir: Path, info: Dict[str, Any]):
        """
        Save post metadata to a text file.
        """
        metadata_file = output_dir / "post_info.txt"

        content = f"""Threads Post Info
{'='*50}
Author: {info['uploader']}
Posted: {info.get('timestamp', 'N/A')}

Caption:
{info['description']}

{'='*50}
"""

        metadata_file.write_text(content, encoding="utf-8")
        print(f"Metadata saved: {metadata_file.name}")
