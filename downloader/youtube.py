"""
YouTube-specific downloader implementation using yt-dlp.
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

try:
    import yt_dlp
except ImportError:
    print("ERROR: yt-dlp not installed. Run: pip install yt-dlp")
    sys.exit(1)

from .base import BaseDownloader
from .utils import (
    check_ffmpeg,
    has_cookies_file,
    sanitize_filename,
    build_ydl_opts,
    DOWNLOAD_DIR,
)
from .progress import progress_hook


class YouTubeDownloader(BaseDownloader):
    """
    YouTube video/audio downloader using yt-dlp.
    
    Features:
    - Download video+audio or separate
    - Subtitle selection (manual + auto-generated)
    - Format selection and listing
    - MP3 audio extraction
    """

    def __init__(self):
        super().__init__("YouTube")

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract YouTube video metadata.
        
        Returns:
            Dictionary with:
            - title, duration, uploader, view_count
            - formats: list of available formats
            - available_subs: list of (lang_code, source, name) tuples
        """
        print("\nFetching video info...\n")

        with yt_dlp.YoutubeDL(build_ydl_opts()) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
            except Exception as e:
                raise Exception(f"Failed to get video info: {e}")

        # Extract subtitle options
        available_subs = self._list_available_subs(info)

        return {
            "title": info.get("title", "N/A"),
            "duration": info.get("duration"),
            "duration_string": info.get("duration_string", "N/A"),
            "uploader": info.get("uploader", "N/A"),
            "view_count": info.get("view_count"),
            "description": info.get("description"),
            "formats": info.get("formats", []),
            "available_subs": available_subs,
            "_raw_info": info,  # Keep raw info for later use
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List all available download formats for the video.
        
        Returns:
            List of format dictionaries
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

            vcodec = fmt.get("vcodec", "none")
            acodec = fmt.get("acodec", "none")
            resolution = fmt.get("resolution", "audio only" if vcodec == "none" else "?")
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")

            if vcodec != "none" and acodec != "none":
                fmt_type = "Video+Audio"
            elif vcodec != "none":
                fmt_type = "Video only"
            else:
                fmt_type = "Audio only"

            codec_str = (
                f"{vcodec}+{acodec}"
                if (vcodec != "none" and acodec != "none")
                else (vcodec if vcodec != "none" else acodec)
            )

            size_str = f"{filesize / 1024 / 1024:.1f} MB" if filesize else "N/A"

            result.append({
                "id": fmt_id,
                "type": fmt_type,
                "codec": codec_str,
                "resolution": resolution,
                "size": size_str,
                "note": fmt.get("format_note", ""),
            })

        return result

    def print_formats(self, url: str):
        """
        Print a nicely formatted table of available formats.
        """
        info = self.get_video_info(url)

        print(f"Title: {info['title']}")
        print(f"Duration: {info['duration_string']}")
        print(f"Uploader: {info['uploader']}")
        if info.get("view_count"):
            print(f"Views: {info['view_count']:,}")
        print()

        formats = self.get_available_formats(url)
        if not formats:
            print("No formats found")
            return

        print("=" * 100)
        print(f"{'ID':<8} {'Type':<12} {'Codec':<22} {'Resolution':<14} {'Size':<12} {'Note'}")
        print("=" * 100)

        for fmt in formats:
            print(
                f"{fmt['id']:<8} {fmt['type']:<12} {fmt['codec']:<22} "
                f"{fmt['resolution']:<14} {fmt['size']:<12} {fmt['note']}"
            )

        print("=" * 100)
        print()
        print("Quick select:")
        print("  bestvideo+bestaudio  -> Best video+audio+subs (auto merge)")
        print("  bestvideo            -> Best video only (no audio)")
        print("  bestaudio            -> Best audio only")
        print()

    def download(
        self,
        url: str,
        options: Dict[str, Any] = None,
    ) -> bool:
        """
        Download YouTube video/audio.
        
        Args:
            url: YouTube URL
            options: Dict with keys:
                - format_choice: str ("best", "best_nosubs", "video", "audio", or format_id)
                - output_dir: str (optional, default: DOWNLOAD_DIR)
                - skip_subs: bool (skip subtitle selection, default: False)
                
        Returns:
            True if successful, False otherwise
        """
        if options is None:
            options = {}

        format_choice = options.get("format_choice", "best")
        output_dir = options.get("output_dir", str(DOWNLOAD_DIR))
        skip_subs = options.get("skip_subs", False)

        if not check_ffmpeg():
            self.print_error("FFmpeg not found, please install ffmpeg")
            return False

        # Get title and subtitle options
        print(f"\nFetching video title...")
        info = self.get_video_info(url)
        title = info["title"]
        safe_title = sanitize_filename(title)

        sub_langs = None if skip_subs else self._pick_subtitles_interactive(info)

        video_dir = Path(output_dir) / safe_title
        video_dir.mkdir(parents=True, exist_ok=True)
        print(f"Output: {video_dir}")

        # Map download mode
        format_labels = {
            "best": ("Best video+audio (choose subs)", "bestvideo+bestaudio/best"),
            "best_nosubs": ("Best video+audio (no subs)", "bestvideo+bestaudio/best"),
            "video": ("Best video only (no audio)", "bestvideo"),
            "audio": ("Best audio only", "bestaudio/best"),
        }

        if format_choice in format_labels:
            label, format_str = format_labels[format_choice]
            print(f"Mode: {label}")
        else:
            format_str = format_choice
            print(f"Mode: Custom format ({format_choice})")

        ydl_opts = build_ydl_opts({
            "format": format_str,
            "outtmpl": str(video_dir / "%(title)s.%(ext)s"),
            "merge_output_format": "mp4",
            "progress_hooks": [progress_hook],
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        })

        # Subtitles: user chooses languages
        if sub_langs:
            ydl_opts.update({
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": sub_langs,
                "subtitlesformat": "srt",
            })

        # Audio mode: convert to mp3
        if format_choice == "audio":
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]

        print()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                extracted_info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(extracted_info)

                if format_choice == "audio":
                    filename = Path(filename).with_suffix(".mp3")

                self.print_success("Download complete!")
                print(f"Video: {filename}")
                if Path(filename).exists():
                    size_mb = Path(filename).stat().st_size / 1024 / 1024
                    print(f"Size: {size_mb:.1f} MB")

                # Check subtitle files
                if sub_langs:
                    subs_found = False
                    for f in sorted(video_dir.glob("*")):
                        if f.suffix in (".srt", ".vtt"):
                            print(f"Sub: {f.name}")
                            subs_found = True
                    if not subs_found:
                        self.print_warning("No subtitles downloaded")

            return True

        except Exception as e:
            self.print_error(f"Download failed: {e}")
            print("\nTip: cookies may be expired or the video requires special permissions.")
            return False

    def download_subtitles(self, url: str, output_dir: str = None) -> bool:
        """
        Download only subtitles for a video (no video/audio).
        
        Args:
            url: YouTube URL
            output_dir: Output directory (default: DOWNLOAD_DIR)
            
        Returns:
            True if successful
        """
        if output_dir is None:
            output_dir = str(DOWNLOAD_DIR)

        Path(output_dir).mkdir(parents=True, exist_ok=True)

        print(f"\nDownloading subtitles...")
        print(f"Output: {output_dir}")

        # Get video info first
        info = self.get_video_info(url)
        sub_langs = self._pick_subtitles_interactive(info)

        if not sub_langs:
            print("No subtitles selected, skipped")
            return False

        print(f"Selected: {', '.join(sub_langs)}")

        ydl_opts = build_ydl_opts({
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": sub_langs,
            "subtitlesformat": "srt",
            "skip_download": True,
            "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
            "quiet": False,
            "no_warnings": False,
        })

        print()
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                extracted_info = ydl.extract_info(url, download=True)

                requested = ydl.prepare_filename(extracted_info)
                stem = Path(requested).stem
                found_any = False
                for f in Path(output_dir).glob(f"{stem}*"):
                    if f.suffix in (".srt", ".vtt"):
                        print(f"Got: {f.name}")
                        found_any = True

                if not found_any:
                    self.print_warning("No subtitles available for this video")

            return True

        except Exception as e:
            self.print_error(f"Subtitle download failed: {e}")
            return False

    # ========== Helper methods ==========

    def _list_available_subs(self, info: Dict[str, Any]) -> List[Tuple[str, str, str]]:
        """
        List all available subtitles for the video.
        
        Returns:
            [(lang_code, source_label, display_name), ...]
        """
        manual = info.get("subtitles") or {}
        auto = info.get("automatic_captions") or {}

        entries: List[Tuple[str, str, str]] = []
        for lang, subs in manual.items():
            name = subs[0].get("name", lang) if subs else lang
            entries.append((lang, "Manual", name))
        for lang, subs in auto.items():
            name = subs[0].get("name", lang) if subs else lang
            entries.append((lang, "Auto-gen", name))

        return entries

    def _pick_subtitles_interactive(self, info: Dict[str, Any]) -> Optional[List[str]]:
        """
        Interactive prompt for the user to pick subtitle languages.
        
        Returns:
            List of language codes, or None to skip
        """
        entries = self._list_available_subs(info)
        if not entries:
            self.print_warning("No subtitles available for this video")
            return None

        print("\nAvailable subtitles:")
        print(f"  {'#':<4} {'Lang':<16} {'Source':<12} {'Name'}")
        print(f"  {'-'*4} {'-'*16} {'-'*12} {'-'*20}")
        for i, (lang, source, name) in enumerate(entries, 1):
            print(f"  {i:<4} {lang:<16} {source:<12} {name}")

        print(f"\n  Enter numbers to pick (comma-separated, e.g. 1,3), press Enter to skip")

        choice = input("Pick subtitles: ").strip()
        if not choice:
            return None

        selected = []
        for part in choice.replace("，", ",").split(","):
            part = part.strip()
            if part.isdigit():
                idx = int(part) - 1
                if 0 <= idx < len(entries):
                    selected.append(entries[idx][0])
        return selected if selected else None
