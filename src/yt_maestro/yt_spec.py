import logging
import os
import shutil
from pathlib import Path

import yt_dlp

from yt_maestro import audio
from yt_maestro.audio import Chapter

AUDIO_FORMAT = "m4a"
QUIET_YT_DLP_LOG = True


def download_from_spec(specs: list[dict]):
    """
    Downloads audio files from YouTube, then applies metadata and chapters
    to each based on a list of specification dictionaries.

    :param specs: A list of dicts, where each item describes one audio file.
    """

    if not isinstance(specs, list):
        logging.error(f"spec must be a list: got {type(specs)}")
        return

    for i, item in enumerate(specs, start=1):
        logging.info(f"Downloading {i} of {len(specs)}...")
        download_item(item)


def download_item(spec: dict) -> str | None:
    """
    Downloads a single YouTube audio file and configures metadata/chapters.

    The audio is saved in the format specified by AUDIO_FORMAT.
    The `spec` dictionary should contain:
      - "url": YouTube URL of the audio source
      - Optional metadata: "title", "artist", "album", "composer", "genre"
      - Optional list of chapter dicts with "title" and "start"

    :param spec: Dictionary describing a single download and processing job.
    :return: Path to the processed audio file if successful, None otherwise.
    """

    if not isinstance(spec, dict):
        logging.error(f"spec must be a dict: got {type(spec)}")
        return None

    # Download the audio file from YouTube
    url = spec.get("url")
    if not url:
        logging.error("spec must include a non-empty 'url'")
        return None
    title = spec.get("title")
    download_path = download_yt_audio(url, title)
    if not download_path:
        return None

    trim_path = None
    metadata_path = None
    chapter_path = None

    try:
        # Configure temporary file location
        audio_dir = Path(download_path).parent
        audio_filename = Path(download_path).name

        # Configure the audio file duration, start, and end
        duration_ms = audio.audio_duration_ms(download_path)
        start_hhmmss, end_hhmmss = spec.get("start"), spec.get("end")
        start_ms = to_milliseconds(start_hhmmss, 0)
        end_ms = to_milliseconds(end_hhmmss, duration_ms)

        # Validate start and end time
        if not validate_time_range(start_ms, end_ms, duration_ms):
            logging.error("Invalid start and end times")
            start_ms, end_ms = 0, duration_ms

        # Trim audio from start_hhmmss to end_hhmmss
        if start_hhmmss is not None or end_hhmmss is not None:
            trim_path = audio_dir / f"trim_{audio_filename}"
            trim_path = audio.trim_audio(download_path, trim_path,
                                         start_ms, end_ms)
        else:
            trim_path = download_path

        # Configure metadata
        metadata = extract_metadata(spec)
        metadata_path = audio_dir / f"meta_{audio_filename}"
        metadata_path = audio.add_metadata(trim_path, metadata_path, metadata)

        # Add chapters
        chapter_path = metadata_path
        if "chapters" in spec:
            chapters = extract_chapters(spec["chapters"], start_ms, end_ms)
            if chapters:
                chapter_path = audio_dir / f"chapter_{audio_filename}"
                chapter_path = audio.add_chapters(metadata_path,
                                                  chapter_path, chapters)

        # Move the processed file to the directory of the artist's album
        final_path = (audio_dir /
                      metadata.get("artist", "Unknown Artist") /
                      metadata.get("album", "Unknown Album") /
                      audio_filename)
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(chapter_path), str(final_path))
        return str(final_path)

    finally:
        # Remove temporary files during the processing
        if chapter_path != download_path:
            temp_paths = {download_path, trim_path, metadata_path}
            for path in temp_paths:
                if os.path.exists(path):
                    os.remove(path)


def download_yt_audio(url: str, title: str = None) -> str | None:
    """
    Downloads a YouTube audio track and saves it as <title>.<AUDIO_FORMAT>.

    :param url: The YouTube video URL to download audio from.
    :param title: Optional custom title for the output file (no extension).
                  If None, the YouTube video's title is used.
    :return: Base path to the downloaded audio file in AUDIO_FORMAT,
             or None if no audio was downloaded.
    """

    download_options = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": AUDIO_FORMAT,
        }],
        "postprocessor_args": {
            "FFmpegExtractAudio": ["-c:a", "aac", "-b:a", "192k"]
        },
        "quiet": QUIET_YT_DLP_LOG,
        "no_warnings": QUIET_YT_DLP_LOG,
        "noplaylist": True,
    }

    if title:
        download_options["outtmpl"] = f"{title}.%(ext)s"

    try:
        with yt_dlp.YoutubeDL(download_options) as ydl:
            info = ydl.extract_info(url, download=True)

        # CHANGE: resolve the final post-processed filepath robustly
        rd = info.get("requested_downloads") or []
        if rd and (rd[0].get("filepath") or rd[0].get("_filename")):
            return rd[0].get("filepath") or rd[0].get("_filename")

        # Fallback for older yt-dlp: derive from pre-pp name but fix extension
        pre = ydl.prepare_filename(info)  # e.g., "title.webm"
        base, _ = os.path.splitext(pre)
        return f"{base}.{AUDIO_FORMAT}"

    except yt_dlp.DownloadError as e:
        logging.error(f"Failed to download {url}: {e}")
        return None


def extract_metadata(spec: dict) -> dict[str, str]:
    """
    Pulls string metadata from spec and fills missing artist/album from composer.
    Sets album_artist to the same value as album.
    Keeps only non-empty strings.
    """

    metadata_keys = ["title", "artist", "album", "composer", "genre"]
    metadata = {
        key: spec[key].strip()
        for key in metadata_keys
        if key in spec and isinstance(spec[key], str)
    }

    # If composer is present, fill artist/album only if missing
    composer = metadata.get("composer")
    if composer:
        metadata.setdefault("artist", composer)
        metadata.setdefault("album", last_name(composer))

    # album_artist should mirror album if album exists
    if "album" in metadata:
        metadata["album_artist"] = metadata["album"]

    return metadata


def extract_chapters(ch_spec: list[dict[str, str]], file_start_ms: int,
                     file_end_ms: int) -> list[Chapter] | None:
    """
    Extracts a sorted list of chapters from a spec.

    Each spec entry must contain:
      - "start": timestamp string (hh:mm:ss, mm:ss, or ss[.ms])
      - "title": optional chapter title

    :param ch_spec: List of chapter dicts from the user spec.
    :param file_start_ms: File start time in milliseconds.
    :param file_end_ms: File end time in milliseconds.
    :return: List of Chapter objects, or None if parsing fails.
    """

    ch_spec_ms: list[tuple[int, str | None]] = []
    for i, ch in enumerate(ch_spec, start=1):
        ch_start_hhmmss = ch.get("start")
        if not ch_start_hhmmss:
            logging.error(f"Ch {i} has no start time")
            return None
        ch_start_ms = to_milliseconds(ch_start_hhmmss.strip(), -1)
        if ch_start_ms < 0:
            logging.error(f"Ch {i} has invalid start time: {ch_start_hhmmss}")
            return None
        title = ch.get("title")
        title = title.strip() if isinstance(title, str) else None
        ch_spec_ms.append((ch_start_ms, title))

    # Sort by start time
    ch_spec_ms.sort(key=lambda t: t[0])

    chapters: list[Chapter] = []
    for i, (ch_start_ms, title) in enumerate(ch_spec_ms):
        ch_end_ms = ch_spec_ms[i + 1][0] \
            if i < len(ch_spec_ms) - 1 else file_end_ms
        if not title:
            title = f"Chapter {i + 1}"
        chapters.append(Chapter(start_ms=ch_start_ms - file_start_ms,
                                end_ms=ch_end_ms - file_start_ms,
                                title=title))

    return chapters


def validate_time_range(start_ms: int, end_ms: int, max_ms: int,
                        min_ms: int = 0) -> bool:
    """
    Validate [start_ms, end_ms) lies within [min_ms, max_ms].
    Returns True if valid, False otherwise.
    """

    if not (min_ms <= start_ms < max_ms):
        logging.error(f"start_ms out of bounds: "
                      f"start={start_ms}ms, min={min_ms}ms, max={max_ms}ms")
        return False
    if not (min_ms <= end_ms <= max_ms):
        logging.error(f"end_ms out of bounds: "
                      f"end={end_ms}ms, min={min_ms}ms, max={max_ms}ms")
        return False
    if end_ms <= start_ms:
        logging.error(f"invalid ordering or zero-length: "
                      f"start={start_ms}ms, end={end_ms}ms")
        return False

    return True


def to_milliseconds(time_hhmmss: str | None, default_ms: int = 0) -> int:
    """
    Converts a timestamp string (hh:mm:ss, mm:ss, ss[.ms]) into milliseconds.
    :return: default_ms if the input cannot be parsed.
    """

    if time_hhmmss is None:
        return default_ms

    parts = time_hhmmss.split(":")
    if not 1 <= len(parts) <= 3:
        logging.error("time_str must be hh:mm:ss, mm:ss, or ss[.ms]")
        return default_ms

    try:
        parts = [float(p) for p in parts]   # Allow fractional seconds
        while len(parts) < 3:
            parts.insert(0, 0)
        h, m, s = parts
        return round((h * 3600 + m * 60 + s) * 1000)
    except ValueError:
        logging.error(f"Invalid timestamp: {time_hhmmss}, "
                      f"defaulting to {default_ms}ms")
        return default_ms


def last_name(full_name: str) -> str:
    """
    Returns the last name of the given full name.
    :return: An empty string if full_name is None.
    """

    if not full_name:
        return ""

    parts = str(full_name).strip().split()
    return parts[-1] if parts else full_name
