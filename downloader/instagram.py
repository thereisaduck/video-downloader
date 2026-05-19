"""
Instagram downloader for posts, Reels, and stories.
Uses yt-dlp as the backend.
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


class InstagramDownloader(BaseDownloader):
    """
    Instagram downloader supporting:
    - Posts and Reels (public and with auth)
    - Carousel posts (multiple media)
    - Metadata extraction (captions, likes, comments)
    - Optional audio extraction
    """

    def __init__(self):
        super().__init__("Instagram")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract Instagram post metadata.
        
        Returns:
            Dictionary with:
            - title, uploader, caption
            - likes, comments
            - formats: available formats
            - is_carousel: bool
            - media_count: int (for carousel)
        """
        print("\nGetting Instagram info...\n")

        try:
            with yt_dlp.YoutubeDL(build_ydl_opts({"quiet": True, "no_warnings": True})) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as e:
            raise Exception(f"Failed to get info: {e}")

        is_carousel = info.get("_type") == "playlist" or len(info.get("formats", [])) > 1
        media_count = len(info.get("entries", [])) if is_carousel else 1

        return {
            "title": info.get("title", "Instagram Post"),
            "uploader": info.get("uploader", "Unknown"),
            "caption": info.get("description", ""),
            "likes": info.get("like_count"),
            "comments": info.get("comment_count"),
            "formats": info.get("formats", []),
            "is_carousel": is_carousel,
            "media_count": media_count,
            "_raw_info": info,
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List available formats (video, image, carousel).
        """
        info = self.get_video_info(url)

        result = []
        if info.get("is_carousel"):
            result.append({
                "id": "all",
                "type": "Carousel (all)",
                "codec": "mixed",
                "resolution": "best",
                "size": f"{info['media_count']} files",
                "note": "Download all images/videos in carousel",
            })
        else:
            result.append({
                "id": "best",
                "type": "Single",
                "codec": "auto",
                "resolution": "best",
                "size": "N/A",
                "note": "Auto best quality",
            })

        return result

    def download(
        self,
        url: str,
        options: Dict[str, Any] = None,
    ) -> bool:
        """
        Download Instagram post/Reel/carousel.
        
        Args:
            url: Instagram URL
            options: Dict with keys:
                - include_captions: bool (default: True)
                - extract_carousel: bool (default: True, for carousel posts)
                - output_dir: str (optional)
                
        Returns:
            True if successful
        """
        if options is None:
            options = {}

        include_captions = options.get("include_captions", False)
        extract_carousel = options.get("extract_carousel", True)
        output_dir = options.get("output_dir", str(DOWNLOAD_DIR))

        if not check_ffmpeg():
            self.print_error("FFmpeg not found")
            return False

        # Get info
        try:
            info = self.get_video_info(url)
        except Exception as e:
            self.print_error(str(e))
            return False

        # Prepare output dir
        uploader = sanitize_filename(info["uploader"])
        title = sanitize_filename(info["title"][:50])
        post_dir = Path(output_dir) / f"{uploader}_{title}"
        post_dir.mkdir(parents=True, exist_ok=True)

        print(f"\nUser: {info['uploader']}")
        print(f"Title: {info['title']}")
        if info.get("likes"):
            print(f"Likes: {info['likes']:,}")
        if info.get("comments"):
            print(f"Comments: {info['comments']:,}")
        if info.get("is_carousel"):
            print(f"Carousel: {info['media_count']} files")
        print(f"Output: {post_dir}")
        print()

        # Build download options
        ydl_opts = build_ydl_opts({
            "outtmpl": str(post_dir / "%(title)s_%(format_id)s.%(ext)s"),
            "format": "best",
            "progress_hooks": [progress_hook],
            "quiet": False,
            "no_warnings": False,
            "noplaylist": not (extract_carousel and info.get("is_carousel")),
        })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            # Save caption/text
            if include_captions and info.get("caption"):
                self._save_caption(post_dir, info)

            # Count downloaded files
            media_files = list(post_dir.glob("*"))
            self.print_success("Download complete!")
            for f in media_files:
                if f.is_file() and f.suffix != ".txt":
                    size_mb = f.stat().st_size / 1024 / 1024
                    print(f"  {f.name} ({size_mb:.1f} MB)")

            return True

        except Exception as e:
            self.print_error(f"Download failed: {e}")
            return False

    # ========== Helper methods ==========

    def _save_caption(self, output_dir: Path, info: Dict[str, Any]):
        """
        Save Instagram caption to a text file.
        """
        caption_file = output_dir / "caption.txt"

        content = f"""Instagram Post Info
{'='*50}
User: {info['uploader']}
Title: {info['title']}

Description:
{info['caption']}

Stats:
- Likes: {info.get('likes', 'N/A')}
- Comments: {info.get('comments', 'N/A')}

{'='*50}
"""

        caption_file.write_text(content, encoding="utf-8")
        print(f"Caption saved: {caption_file.name}")
