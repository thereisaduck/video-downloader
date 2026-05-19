# Multi-Platform Social Media Downloader v2.1

A modular video/media downloader supporting YouTube, Twitter/X, TikTok, Instagram, and Threads.

## Features

### YouTube
- Video + audio with subtitle download
- Manual & auto-generated subtitles
- Custom format ID selection
- Audio-only MP3 extraction

### Twitter/X
- Videos, images, and GIFs from posts
- Thread detection and full-thread download
- Mixed media with sequential naming (_01, _02, ...)

### TikTok
- Best quality auto-select
- Video + audio merge or separate
- Audio extraction to MP3

### Instagram
- Single posts, Reels, and carousels
- All carousel media downloaded
- Mixed media with sequential naming

### Threads
- Video and image post download
- Multi-image post support
- Sequential media naming

## Project Structure

```
downloader/                   # Core package
├── __init__.py             # Package exports (v2.1.0)
├── base.py                 # Abstract BaseDownloader class
├── utils.py                # Shared utilities (cookies, ffmpeg, rename, detect)
├── progress.py             # Download progress hook
├── youtube.py              # YouTube downloader
├── twitter.py              # Twitter/X downloader
├── tiktok.py               # TikTok downloader
├── instagram.py            # Instagram downloader
└── threads.py              # Threads.net downloader

downloader.py                # Main entry point
downloader.bat               # Windows launcher
.gitignore                   # Ignores downloads/, cookies.txt, ffmpeg binaries
requirements.txt             # Python dependencies
ffmpeg-*/                    # FFmpeg binaries (git-ignored)
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

Or run the batch file (auto-installs):
```bash
downloader.bat
```

### 2. FFmpeg

Place FFmpeg in a folder matching `ffmpeg-*/` at the project root. The tool auto-detects it from `ffmpeg-*/bin/`.

Recommended: [gyan.dev FFmpeg essentials build](https://www.gyan.dev/ffmpeg/builds/)

### 3. Cookies (optional)

YouTube may require cookies for age-restricted or region-locked content. Other platforms (Twitter, TikTok, Instagram, Threads) usually work without cookies, but add one if you hit login walls.

Set cookies interactively:

```bash
python downloader.py --set-cookie
```

Or paste a raw cookie string:

```bash
python downloader.py --save-cookie
```

This creates a `cookies.txt` (Netscape format) in the project root. The file is git-ignored.

Alternatively, manually edit `cookies.txt` — any valid Netscape-format cookie file works with yt-dlp.

### 4. Download

#### Method A: Interactive menu

```bash
python downloader.py
```

#### Method B: Pass URL directly (auto-detects platform)

```bash
python downloader.py <url>
```

Examples:

```bash
python downloader.py https://www.youtube.com/watch?v=...
python downloader.py https://x.com/user/status/...
python downloader.py https://www.tiktok.com/@user/video/...
python downloader.py https://www.instagram.com/p/...
python downloader.py https://www.threads.net/@user/post/...
```

### Post-download rename

After download finishes, you get a rename prompt:

```
Rename options:
  [1] Rename folder + all files
  [2] Rename folder only
  [3] Rename one file
  [4] Skip
```

Option [1] uses the folder name as the default file base name (press Enter to confirm).

Twitter and Threads mixed-media posts (video + images) are automatically renamed with sequential suffixes: `PostName_01.jpg`, `PostName_02.mp4`, ...

## Architecture

### Modular design

Each platform has its own downloader class inheriting from `BaseDownloader`:

```python
from downloader import YouTubeDownloader

downloader = YouTubeDownloader()
info = downloader.get_video_info(url)
downloader.download(url, {"format_choice": "best"})
```

### Shared utilities

`utils.py` provides cross-platform helpers:
- Platform auto-detection (`detect_platform_from_url`)
- Cookies management (Netscape format)
- FFmpeg detection
- Filename sanitization
- Post-download rename (`rename_output_folder`)

### Common interface

All downloaders implement:
- `get_video_info(url)` — extract metadata
- `get_available_formats(url)` — list quality/formats
- `download(url, options)` — download media

## Troubleshooting

### FFmpeg not found

Make sure a `ffmpeg-*/bin/` folder exists at project root with `ffmpeg.exe` inside.

### Cannot get video info

- URL may be invalid, deleted, or private
- YouTube: cookies may be expired — re-run `python downloader.py --set-cookie`
- Other platforms: try adding cookies or check if the post is still available

### Encoding issues (Windows GBK)

The tool uses plain ASCII/English in UI text to avoid UnicodeEncodeError on Chinese Windows. This is by design.

### Platform download fails

**Causes**:
- yt-dlp does not support this URL format
- Account restrictions or region locks
- Media is no longer available

**Fixes**:
- Update yt-dlp: `pip install -U yt-dlp`
- Make sure cookies are valid
- Verify the link is accessible in a browser

## Output Directory

All downloads are saved to `downloads/` with this structure:

```
downloads/
├── Video_Title/
│   ├── Video_Title.mp4
│   ├── Video_Title.en.srt
│   └── Video_Title.zh.srt
├── uploader_post_titlehash/
│   ├── image_01.jpg
│   ├── video.mp4
│   └── metadata.txt
├── creator_TikTok_title/
│   └── video.mp4
└── user_post_title/
    ├── media_01.jpg
    ├── media_02.jpg
    └── caption.txt
```

## Development

### Adding a new platform

To add support for a new platform:

1. Create a new file `newplatform.py` under `downloader/`
2. Create a class inheriting from `BaseDownloader`
3. Implement required methods: `get_video_info()`, `download()`, `get_available_formats()`
4. Export the new class in `downloader/__init__.py`
5. Add a routing function in `downloader.py`

### Extending existing features

To extend a downloader (e.g. adding proxy support):

```python
from downloader import YouTubeDownloader

class ExtendedYouTubeDownloader(YouTubeDownloader):
    def download(self, url, options=None):
        # Custom logic
        options = options or {}
        options['proxy'] = 'socks5://...'
        return super().download(url, options)
```

## License

MIT License

## FAQ

**Q: Does it support playlist downloads?**  
A: Not currently. Focused on single video/post downloads.

**Q: Does it support livestream downloads?**  
A: Not currently. Feature requests welcome.

**Q: How do I run in headless mode?**  
A: Pass the URL directly: `python downloader.py <URL>`

**Q: Does it support proxies?**  
A: Indirectly via environment variables. You can modify `build_ydl_opts()` in `utils.py` to add proxy support.

---

**Version**: 2.1.0  
**Last updated**: 2026-05-19  
**Maintainer**: Multi-Platform Downloader Team
