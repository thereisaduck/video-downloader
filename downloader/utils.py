"""
Shared utilities for all downloader modules:
- Path and environment setup
- Cookies management (Netscape format)
- FFmpeg detection
- Filename sanitization
- Common configuration
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone


# ========== Global config ==========
WORKSPACE_DIR = Path(__file__).parent.parent
DOWNLOAD_DIR = WORKSPACE_DIR / "downloads"
COOKIES_FILE = WORKSPACE_DIR / "cookies.txt"

DOWNLOAD_DIR.mkdir(exist_ok=True)


def _find_ffmpeg_dir() -> Path | None:
    """Find ffmpeg binary directory (glob ffmpeg-*/bin/ in workspace)."""
    for pattern in ["ffmpeg-*", "ffmpeg*"]:
        for d in sorted(WORKSPACE_DIR.glob(pattern), reverse=True):
            if d.is_dir() and (d / "bin" / "ffmpeg.exe").exists():
                return d / "bin"
    return None


def _ensure_ffmpeg_in_path():
    """Add ffmpeg dir to PATH if found and not already present."""
    ffmpeg_dir = _find_ffmpeg_dir()
    if ffmpeg_dir and str(ffmpeg_dir) not in os.environ["PATH"]:
        os.environ["PATH"] = str(ffmpeg_dir) + os.pathsep + os.environ["PATH"]


# ========== FFmpeg ==========

def check_ffmpeg() -> bool:
    """Check if ffmpeg is available (PATH or project ffmpeg-*/bin/)."""
    _ensure_ffmpeg_in_path()
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


# ========== Cookies (Netscape format) ==========

def has_cookies_file() -> bool:
    """Check if cookies.txt exists and is non-empty."""
    return COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0


def _cookie_domains() -> list[str]:
    """Domains to write cookies for (covers all supported platforms)."""
    return [".youtube.com", ".twitter.com", ".x.com", ".instagram.com", ".threads.net"]


def save_cookies_from_user_input():
    """
    Interactively enter cookies, saved as Netscape-format cookies.txt.
    """
    print("\n" + "=" * 60)
    print("  Set Cookies")
    print("=" * 60)
    print()
    print("Get cookie values from your browser:")
    print("  Open site -> F12 -> Application -> Cookies")
    print()

    required_cookies = [
        ("LOGIN_INFO",         "Login info"),
        ("VISITOR_INFO1_LIVE", "Visitor ID"),
        ("__Secure-3PAPISID",  "Secure token"),
        ("__Secure-3PSID",     "Session token"),
        ("__Secure-3PSIDTS",   "Session timestamp"),
    ]

    cookies = {}
    for name, desc in required_cookies:
        val = input(f"  {name} ({desc}): ").strip()
        if val:
            cookies[name] = val

    if not cookies:
        print("No cookies entered")
        return

    write_netscape_cookies(cookies)
    print(f"Cookies saved to: {COOKIES_FILE}")


def save_cookies_from_raw_string():
    """
    Paste raw cookie string to write cookies.txt.
    Supports two formats:
      1. Netscape format (paste directly)
      2. name=value; name=value string (auto-convert)
    """
    print("\n" + "=" * 60)
    print("  Paste Cookie String")
    print("=" * 60)
    print()
    print("Supported formats:")
    print("  A) Netscape format (full cookies.txt content)")
    print("  B) name=value; name=value string")

    choice = input("\nFormat A or B? [A/B]: ").strip().upper()

    print("\nPaste cookie content (press Enter, then Ctrl+Z then Enter to finish):")

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    raw = "\n".join(lines).strip()
    if not raw:
        print("Nothing pasted")
        return

    if choice == "B":
        cookies = parse_cookie_string(raw)
        write_netscape_cookies(cookies)
    else:
        if not raw.startswith("# Netscape HTTP Cookie File"):
            raw = "# Netscape HTTP Cookie File\n# yt-dlp cookies\n\n" + raw
        COOKIES_FILE.write_text(raw, encoding="utf-8")

    print(f"Cookies saved to: {COOKIES_FILE}")


def parse_cookie_string(raw: str) -> dict:
    """Parse name=value; name2=value cookie string."""
    cookies = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            key, _, val = part.partition("=")
            cookies[key.strip()] = val.strip()
    return cookies


def write_netscape_cookies(cookies: dict):
    """Write cookie dict as Netscape format, covering all supported domains."""
    expires = int(datetime.now(timezone.utc).timestamp()) + 365 * 24 * 3600

    lines = [
        "# Netscape HTTP Cookie File",
        "# This file is used by downloader to authenticate.",
        "",
    ]

    for domain in _cookie_domains():
        for name, value in cookies.items():
            lines.append(f"{domain}\tTRUE\t/\tTRUE\t{expires}\t{name}\t{value}")

    COOKIES_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_cookies(for_platform: str = "youtube") -> bool:
    """
    Ensure cookies are available. Only prompts for platforms that need auth.
    
    Args:
        for_platform: "youtube", "twitter", etc. Non-YouTube skips prompt.
    """
    if has_cookies_file():
        return True

    if for_platform != "youtube":
        # Twitter/TikTok/Instagram/Threads work without cookies
        return False

    print("\nNo cookies.txt found. YouTube may need cookies for some content.")
    print()
    print("  [1] Enter key cookies (recommended, 3-5 values)")
    print("  [2] Paste full cookie string")
    print("  [3] Skip (some videos may fail)")
    print("  [q] Quit")

    choice = input("\nPick [1/2/3/q]: ").strip()

    if choice == "1":
        save_cookies_from_user_input()
    elif choice == "2":
        save_cookies_from_raw_string()
    elif choice == "3":
        print("Skipping cookies setup")
        return False
    elif choice.lower() == "q":
        print("Quit")
        sys.exit(0)
    else:
        print("Invalid option")
        sys.exit(1)

    return has_cookies_file()


# ========== Filename handling ==========

def sanitize_filename(name: str) -> str:
    """Remove illegal filesystem characters from filename."""
    illegal = '<>:"/\\|?*'
    for c in illegal:
        name = name.replace(c, "_")
    name = name.strip(". ")
    return name[:200] if len(name) > 200 else name


# ========== yt-dlp config builder ==========

def build_ydl_opts(extra_opts: dict = None) -> dict:
    """Build yt-dlp options dict with auto cookies + ffmpeg path."""
    opts = {
        "quiet": True,
        "no_warnings": True,
    }
    ffmpeg_dir = _find_ffmpeg_dir()
    if ffmpeg_dir:
        opts["ffmpeg_location"] = str(ffmpeg_dir)
    if extra_opts:
        opts.update(extra_opts)
    if has_cookies_file():
        opts["cookiefile"] = str(COOKIES_FILE)
    return opts


def detect_platform_from_url(url: str) -> str:
    """Auto-detect platform from URL."""
    url_lower = url.lower()
    
    if "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "twitter.com" in url_lower or "x.com" in url_lower or "t.co" in url_lower:
        return "twitter"
    elif "tiktok.com" in url_lower or "vm.tiktok.com" in url_lower or "vt.tiktok.com" in url_lower:
        return "tiktok"
    elif "threads.net" in url_lower:
        return "threads"
    elif "instagram.com" in url_lower or "instagr.am" in url_lower:
        return "instagram"
    else:
        return "unknown"


# ========== Post-download rename ==========

def rename_output_folder(current_dir: str | Path) -> str | None:
    """
    After download, prompt the user to rename the output folder and/or its files.
    
    Args:
        current_dir: Path to the downloaded folder
        
    Returns:
        New directory path if renamed, or None if skipped
    """
    current_dir = Path(current_dir)
    
    if not current_dir.exists():
        return None
    
    print("\n" + "=" * 50)
    print("  [Rename]")
    print("=" * 50)
    print(f"\nCurrent folder: {current_dir.name}")
    print(f"Path: {current_dir}")
    
    # List files in the folder
    files = [f for f in current_dir.iterdir() if f.is_file()]
    if files:
        print(f"\nFiles ({len(files)}):")
        for f in files:
            size_mb = f.stat().st_size / 1024 / 1024 if f.is_file() else 0
            print(f"  - {f.name} ({size_mb:.1f} MB)")
    
    print("\nRename options:")
    print("  [1] Rename folder + all files")
    print("  [2] Rename folder only")
    print("  [3] Rename one file")
    print("  [4] Skip")
    
    choice = input("\nPick [1-4]: ").strip()
    
    if choice == "4" or not choice:
        return None
    
    if choice == "1":
        # Rename folder + files
        new_folder_name = input("New folder name: ").strip()
        if not new_folder_name:
            print("Skipped")
            return None
        new_folder_name = sanitize_filename(new_folder_name)
        
        new_base_name = input(f"New file basename (press Enter to use \"{new_folder_name}\"): ").strip()
        if not new_base_name:
            new_base_name = new_folder_name
        
        # Rename folder
        new_dir = current_dir.parent / new_folder_name
        try:
            current_dir.rename(new_dir)
            print(f"Folder renamed: {current_dir.name} -> {new_dir.name}")
            current_dir = new_dir
        except Exception as e:
            print(f"Folder rename failed: {e}")
            return None
        
        # Rename files
        files = sorted([f for f in current_dir.iterdir() if f.is_file()])
        count = 1
        for f in files:
            ext = f.suffix
            if len(files) == 1:
                new_fname = f"{new_base_name}{ext}"
            else:
                new_fname = f"{new_base_name}_{count:02d}{ext}"
                count += 1
            try:
                new_path = f.parent / new_fname
                f.rename(new_path)
                print(f"File renamed: {f.name} -> {new_fname}")
            except Exception as e:
                print(f"Skip {f.name}: {e}")
        
        return str(current_dir)
    
    elif choice == "2":
        # Rename folder only
        new_folder_name = input("New folder name: ").strip()
        if not new_folder_name:
            print("Skipped")
            return None
        new_folder_name = sanitize_filename(new_folder_name)
        
        new_dir = current_dir.parent / new_folder_name
        try:
            current_dir.rename(new_dir)
            print(f"Folder renamed: {current_dir.name} -> {new_dir.name}")
            return str(new_dir)
        except Exception as e:
            print(f"Rename failed: {e}")
            return None
    
    elif choice == "3":
        # Rename one file only
        files = sorted([f for f in current_dir.iterdir() if f.is_file()])
        if not files:
            print("No files in folder")
            return None
        
        print("\nFiles:")
        for i, f in enumerate(files, 1):
            print(f"  [{i}] {f.name}")
        
        try:
            file_idx = int(input("\nPick file number: ").strip()) - 1
            if file_idx < 0 or file_idx >= len(files):
                print("Invalid number")
                return None
        except ValueError:
            print("Invalid input")
            return None
        
        target = files[file_idx]
        new_name = input(f"New filename: ").strip()
        if not new_name:
            print("Skipped")
            return None
        
        # Keep original extension if no extension given
        if "." not in new_name:
            new_name += target.suffix
        
        new_name = sanitize_filename(new_name)
        new_path = target.parent / new_name
        
        try:
            target.rename(new_path)
            print(f"File renamed: {target.name} -> {new_name}")
        except Exception as e:
            print(f"Rename failed: {e}")
        
        return str(current_dir)
    
    return None
