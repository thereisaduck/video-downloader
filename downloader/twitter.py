"""
Twitter/X downloader for posts with images, videos, and GIFs.
Uses yt-dlp as the backend with custom handling for media extraction.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import json

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


class TwitterDownloader(BaseDownloader):
    """
    Twitter/X post downloader supporting:
    - Single posts with videos, images, GIFs
    - Thread detection and download options
    - Metadata extraction (tweet text, author, timestamp)
    """

    def __init__(self):
        super().__init__("Twitter/X")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract Twitter post metadata.
        
        Returns:
            Dictionary with:
            - title, uploader, description (tweet text)
            - formats: available media formats
            - is_thread: bool
            - thread_url: URL for full thread (if thread detected)
        """
        print("\nFetching tweet info...\n")

        try:
            with yt_dlp.YoutubeDL(build_ydl_opts({"quiet": True, "no_warnings": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise Exception(f"Failed to get tweet info: {e}")

        is_thread = self._detect_thread(url, info)

        return {
            "title": info.get("title", "Twitter Post"),
            "uploader": info.get("uploader", "Unknown"),
            "description": info.get("description", ""),
            "timestamp": info.get("upload_date"),
            "formats": info.get("formats", []),
            "is_thread": is_thread,
            "thread_url": url if is_thread else None,
            "_raw_info": info,
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List available media formats (video, images, GIFs).
        """
        info = self.get_video_info(url)
        formats = info.get("formats", [])

        result = []
        if not formats:
            # No video formats, return generic options
            result.append({
                "id": "default",
                "type": "Mixed media",
                "codec": "auto",
                "resolution": "best",
                "size": "N/A",
                "note": "Auto best quality",
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
        Download Twitter post media.
        
        Args:
            url: Twitter/X URL
            options: Dict with keys:
                - thread_mode: str ("single", "thread", "ask")
                - include_images: bool (default: True)
                - include_metadata: bool (default: False)
                - output_dir: str (optional)
                
        Returns:
            True if successful
        """
        if options is None:
            options = {}

        thread_mode = options.get("thread_mode", "ask")
        include_metadata = options.get("include_metadata", False)
        output_dir = options.get("output_dir", str(DOWNLOAD_DIR))

        if not check_ffmpeg():
            self.print_error("FFmpeg not found")
            return False

        # Get tweet info
        try:
            info = self.get_video_info(url)
        except Exception as e:
            self.print_error(str(e))
            return False

        # Decide download mode
        download_thread = self._decide_thread_mode(info, thread_mode)

        # Prepare output directory
        uploader = sanitize_filename(info["uploader"])
        title = sanitize_filename(info["title"][:50])
        post_dir = Path(output_dir) / f"{uploader}_{title}"
        post_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nAuthor: {info['uploader']}")
        print(f"Content: {info['description'][:100]}...")
        print(f"Output: {post_dir}")
        print(f"Mode: {'Entire thread' if download_thread else 'Single post'}")
        print()

        # Download — no format restriction, let yt-dlp grab all media (images+video)
        target_url = info["thread_url"] if download_thread else url

        # Use temp template, rename sequentially later
        temp_template = str(post_dir / "%(title)s_%(format_id)s.%(ext)s")

        ydl_opts = build_ydl_opts({
            "outtmpl": temp_template,
            "progress_hooks": [progress_hook],
            "quiet": False,
            "no_warnings": False,
            # Thread mode allows playlist; single post also gets all media entries
            "noplaylist": not download_thread,
        })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([target_url])

            # Rename all media files sequentially -> _1, _2, _3 ...
            self._rename_media_sequential(post_dir, f"{uploader}_{title}")

            # Save metadata
            if include_metadata:
                self._save_metadata(post_dir, info)

            self.print_success("Download complete!")
            return True

        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    # ========== Helper methods ==========

    def _rename_media_sequential(self, post_dir: Path, base_name: str):
        """
        Rename all media files in the download directory sequentially to base_1.ext, base_2.ext ...

        Skips .txt and other non-media files.
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
            # Single file, still rename for a cleaner name
            if media_files:
                ext = media_files[0].suffix
                new_name = f"{base_name}{ext}"
                new_path = post_dir / new_name
                try:
                    media_files[0].rename(new_path)
                    print(f"[RENAME] {media_files[0].name} -> {new_name}")
                except Exception as e:
                    print(f"[SKIP] Rename failed: {e}")
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
                print(f"  [{idx}] [SKIP] {f.name}: {e}")

    def _detect_thread(self, url: str, info: Dict[str, Any]) -> bool:
        """
        Detect if this is a tweet thread.
        Simple heuristic: currently relies on user to decide interactively.
        """
        # Simplified version; real detection needs more complex logic
        # For now, let the user decide interactively
        return False  # Let user decide in interactive mode

    def _decide_thread_mode(self, info: Dict[str, Any], thread_mode: str) -> bool:
        """
        Decide whether to download the thread.
        
        Args:
            info: Video info from get_video_info()
            thread_mode: "ask", "thread", or "single"
            
        Returns:
            True if should download thread, False for single post
        """
        if thread_mode == "thread":
            return True
        elif thread_mode == "single":
            return False
        else:  # "ask"
            if not info.get("is_thread"):
                print("This does not appear to be a thread")
                return False

            print("\nDownload entire thread?")
            print("  [1] Single post")
            print("  [2] Entire thread")
            choice = input("\nPick [1/2]: ").strip()

            return choice == "2"

    def _save_metadata(self, output_dir: Path, info: Dict[str, Any]):
        """
        Save tweet metadata to a text file.
        """
        metadata_file = output_dir / "metadata.txt"

        content = f"""Twitter/X Post Metadata
{'='*50}
Author: {info['uploader']}
Timestamp: {info.get('timestamp', 'N/A')}
Content: 
{info['description']}

Downloaded: now
{'='*50}
"""

        metadata_file.write_text(content, encoding="utf-8")
        print(f"Metadata saved: {metadata_file.name}")
