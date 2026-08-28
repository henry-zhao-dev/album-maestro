"""YouTube audio downloads through yt-dlp."""

import logging
from pathlib import Path

import yt_dlp

DEFAULT_AUDIO_FORMAT = "m4a"

logger = logging.getLogger(__name__)


def download_audio(
    url: str,
    output_dir: Path,
    *,
    title: str | None = None,
    audio_format: str = DEFAULT_AUDIO_FORMAT,
    bitrate: str = "192k",
    quiet: bool = True,
) -> Path | None:
    """Download one URL and return its post-processed audio path."""

    filename_template = f"{title}.%(ext)s" if title else "%(title)s.%(ext)s"
    output_template = output_dir / filename_template
    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_template),
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": audio_format}
        ],
        "postprocessor_args": {"FFmpegExtractAudio": ["-c:a", "aac", "-b:a", bitrate]},
        "quiet": quiet,
        "no_warnings": quiet,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            # Post-processing may change the extension, so prefer yt-dlp's
            # reported final path over the original prepared filename.
            downloads = info.get("requested_downloads") or []
            if downloads and (
                downloads[0].get("filepath") or downloads[0].get("_filename")
            ):
                return Path(downloads[0].get("filepath") or downloads[0]["_filename"])

            prepared_path = Path(ydl.prepare_filename(info))
            return prepared_path.with_suffix(f".{audio_format}")
    except yt_dlp.DownloadError as error:
        logger.error("Download failed for %s: %s", url, error)
        return None
