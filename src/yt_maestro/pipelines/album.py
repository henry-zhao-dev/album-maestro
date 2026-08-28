"""Pipeline for downloading and processing complete albums."""

import logging
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import audio, downloader
from yt_maestro.models import Album, Chapter, TrackRequest


class PipelineError(ValueError):
    """Raised when validated catalog data cannot be processed into audio."""


def process_album(album: Album, output_dir: str | Path = ".") -> list[Path]:
    """Resolve and process every track in an album."""

    return process_requests(album.requests(), output_dir)


def process_requests(
    tracks: Sequence[TrackRequest], output_dir: str | Path = "."
) -> list[Path]:
    """Process tracks sequentially and return the successfully created files."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for index, track in enumerate(tracks, start=1):
        logging.info("Processing %s of %s", index, len(tracks))
        try:
            output = process_track(track, destination)
        except PipelineError as error:
            logging.error("cannot process track %s: %s", index, error)
            continue
        if output is not None:
            outputs.append(output)
    return outputs


def process_track(track: TrackRequest, output_dir: str | Path = ".") -> Path | None:
    """Download, process, and organize one validated track."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".yt-maestro-", dir=destination) as temp:
        work_dir = Path(temp)
        downloaded = downloader.download_audio(track.url, work_dir, title=track.title)
        if downloaded is None:
            return None

        duration_ms = audio.audio_duration_ms(downloaded)
        start_ms, end_ms = resolve_time_range(track, duration_ms)
        current = str(downloaded)

        if track.start_ms is not None or track.end_ms is not None:
            current = audio.trim_audio(
                current, work_dir / f"trim-{downloaded.name}", start_ms, end_ms
            )

        metadata = track.metadata()
        current = audio.add_metadata(
            current, work_dir / f"metadata-{downloaded.name}", metadata
        )

        if track.chapters:
            chapters = resolve_chapters(track.chapters, start_ms, end_ms)
            current = audio.add_chapters(
                current, work_dir / f"chapters-{downloaded.name}", chapters
            )

        artist = metadata.get(
            "album_artist", metadata.get("artist", "Unknown Artist")
        )
        album = metadata.get("album", "Unknown Album")
        final_path = destination / artist / album / downloaded.name
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(current, final_path)
        return final_path


def resolve_time_range(track: TrackRequest, duration_ms: int) -> tuple[int, int]:
    """Resolve optional trim bounds against the downloaded file duration."""

    if duration_ms <= 0:
        raise PipelineError("downloaded audio has no valid duration")

    start_ms = track.start_ms if track.start_ms is not None else 0
    end_ms = track.end_ms if track.end_ms is not None else duration_ms
    if not 0 <= start_ms < end_ms <= duration_ms:
        raise PipelineError(
            f"time range {start_ms}ms..{end_ms}ms is outside "
            f"the {duration_ms}ms recording"
        )
    return start_ms, end_ms


def resolve_chapters(
    chapters: Sequence[Chapter], start_ms: int, end_ms: int
) -> list[Chapter]:
    """Convert source-relative chapter declarations to output timestamps."""

    for chapter in chapters:
        if not start_ms <= chapter.start_ms < end_ms:
            raise PipelineError(
                f"chapter at {chapter.start_ms}ms is outside the selected time range"
            )

    return [
        Chapter(
            start_ms=chapter.start_ms - start_ms,
            end_ms=(
                chapters[index + 1].start_ms
                if index + 1 < len(chapters)
                else end_ms
            )
            - start_ms,
            title=chapter.title or f"Chapter {index + 1}",
        )
        for index, chapter in enumerate(chapters)
    ]
