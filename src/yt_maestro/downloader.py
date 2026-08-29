"""YouTube audio downloads through yt-dlp."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

import yt_dlp
from yt_dlp.utils import DownloadError

DEFAULT_AUDIO_FORMAT = "m4a"
DEFAULT_AUDIO_BITRATE_KBPS = 192


class DownloaderError(RuntimeError):
    """Raised when yt-dlp cannot produce the requested audio file."""


def download_audio(
    url: str,
    output_dir: str | Path,
    *,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
    bitrate_kbps: int = DEFAULT_AUDIO_BITRATE_KBPS,
    quiet: bool = True,
) -> Path:
    """Download one URL and return its post-processed audio path."""

    url = url.strip()
    audio_format = audio_format.strip().removeprefix(".").lower()
    if not url:
        raise ValueError("url must not be empty")
    if not audio_format:
        raise ValueError("audio_format must not be empty")
    if bitrate_kbps <= 0:
        raise ValueError("bitrate_kbps must be positive")

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    options: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(destination / "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": audio_format,
                "preferredquality": str(bitrate_kbps),
            }
        ],
        "quiet": quiet,
        "no_warnings": quiet,
        "noplaylist": True,
    }

    try:
        # yt-dlp's public options dictionary is broader than its type stub.
        with yt_dlp.YoutubeDL(cast(Any, options)) as ydl:
            info = ydl.extract_info(url, download=True)
            if not isinstance(info, Mapping):
                raise DownloaderError("yt-dlp returned no download information")
            return _downloaded_path(ydl, info, audio_format)
    except DownloadError as error:
        raise DownloaderError(f"download failed for {url}: {error}") from error


def _downloaded_path(
    ydl: yt_dlp.YoutubeDL,
    info: Mapping[str, Any],
    audio_format: str,
) -> Path:
    """Resolve the final path reported after yt-dlp post-processing."""

    downloads = info.get("requested_downloads")
    if isinstance(downloads, list) and downloads:
        download = downloads[0]
        if isinstance(download, Mapping):
            path = download.get("filepath") or download.get("_filename")
            if isinstance(path, str) and path and Path(path).is_file():
                return Path(path)

    # Older extractors may only expose the filename prepared before audio
    # post-processing, so replace its extension with the requested format.
    prepared_path = Path(ydl.prepare_filename(cast(Any, dict(info))))
    final_path = prepared_path.with_suffix(f".{audio_format}")
    if final_path.is_file():
        return final_path
    raise DownloaderError("yt-dlp completed without producing an audio file")
