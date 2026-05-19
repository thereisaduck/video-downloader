"""
Base abstract class for all downloader implementations.
Defines the common interface that all platform-specific downloaders must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class BaseDownloader(ABC):
    """
    Abstract base class for all platform-specific downloaders.
    
    Subclasses must implement:
    - get_video_info(url)
    - download(url, options)
    
    Subclasses may override:
    - Any helper method to customize behavior
    """

    def __init__(self, name: str = "BaseDownloader"):
        """
        Initialize downloader.
        
        Args:
            name: Friendly name for the downloader (e.g., "YouTube", "TikTok")
        """
        self.name = name

    @abstractmethod
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract metadata from a URL without downloading.
        
        Args:
            url: The URL to analyze
            
        Returns:
            Dictionary with keys:
            - "title": str (video/post title)
            - "duration": int or None (in seconds)
            - "uploader": str (creator/channel name)
            - "description": str or None
            - "formats": List[Dict] (available quality options)
            - "available_subs": List[tuple] or None (for subtitles)
            - Any other platform-specific metadata
            
        Raises:
            Exception: If URL is invalid or info cannot be extracted
        """
        pass

    @abstractmethod
    def download(self, url: str, options: Dict[str, Any] = None) -> bool:
        """
        Download video/content from URL.
        
        Args:
            url: The URL to download from
            options: Download options dictionary (format_id, output_dir, etc.)
                    Platform-specific options should be handled gracefully
            
        Returns:
            True if download succeeded, False otherwise
            
        Raises:
            Exception: If download fails critically
        """
        pass

    @abstractmethod
    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """
        List all available download formats/qualities.
        
        Args:
            url: The URL to check
            
        Returns:
            List of format dictionaries with keys:
            - "id": str (format ID for downloading)
            - "type": str ("video", "audio", "mixed", etc.)
            - "codec": str (vcodec+acodec)
            - "resolution": str ("720p", "audio only", etc.)
            - "size": str ("100.5 MB", "N/A", etc.)
            - Any other platform-specific info
        """
        pass

    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize filename for the platform.
        
        Args:
            name: Original filename/title
            
        Returns:
            Safe filename with illegal characters removed
        """
        from .utils import sanitize_filename
        return sanitize_filename(name)

    def _ensure_output_dir(self, output_dir: str = None) -> Path:
        """
        Ensure output directory exists, create if necessary.
        
        Args:
            output_dir: Directory path, or None for default
            
        Returns:
            Path object to the directory
        """
        from .utils import DOWNLOAD_DIR
        
        if output_dir is None:
            output_dir = str(DOWNLOAD_DIR)
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def print_section(self, title: str, width: int = 50):
        """Print a formatted section header"""
        print("\n" + "=" * width)
        print(f"  {title}")
        print("=" * width)
        print()

    def print_info(self, **kwargs):
        """Print formatted key-value pairs"""
        for key, value in kwargs.items():
            print(f"{key}: {value}")

    def print_error(self, msg: str):
        """Print error message"""
        print(f"\nERROR: {msg}")

    def print_success(self, msg: str):
        """Print success message"""
        print(f"\nOK: {msg}")

    def print_warning(self, msg: str):
        """Print warning message"""
        print(f"\nWARNING: {msg}")
