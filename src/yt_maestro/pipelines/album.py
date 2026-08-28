"""Pipeline for downloading and building complete albums."""

import logging
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import audio, downloader
from yt_maestro.models import Album, Chapter, TrackRequest


class PipelineError(ValueError):
    """Raised when catalog data cannot be transformed into output audio."""


def download_album(album: Album, output_dir: str | Path = ".") -> list[Path]:
    """Download, transform, and organize every track in an album."""

    return download_tracks(album.requests(), output_dir)


def download_tracks(
    tracks: Sequence[TrackRequest], output_dir: str | Path = "."
) -> list[Path]:
    """Download tracks sequentially and return the created files."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for index, track in enumerate(tracks, start=1):
        logging.info("Downloading track %s of %s", index, len(tracks))
        try:
            output = download_track(track, destination)
        except PipelineError as error:
            logging.error("cannot download track %s: %s", index, error)
            continue
        if output is not None:
            outputs.append(output)
    return outputs


def download_track(track: TrackRequest, output_dir: str | Path = ".") -> Path | None:
    """Download, transform, and organize one validated track."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".yt-maestro-", dir=destination) as temp:
        work_dir = Path(temp)
        downloaded = downloader.download_audio(track.url, work_dir, title=track.title)
        if downloaded is None:
            return None

        duration_ms = audio.audio_duration_ms(downloaded)
        audio_start_ms, audio_end_ms = resolve_time_range(track, duration_ms)
        # Each processing stage consumes the file produced by the previous one.
        current = str(downloaded)

        if track.start_ms is not None or track.end_ms is not None:
            current = audio.trim_audio(
                current,
                work_dir / f"trim-{downloaded.name}",
                audio_start_ms,
                audio_end_ms,
            )

        metadata = track.metadata()
        current = audio.add_metadata(
            current, work_dir / f"metadata-{downloaded.name}", metadata
        )

        if track.chapters:
            chapters = resolve_chapters(
                track.chapters, audio_start_ms, audio_end_ms
            )
            current = audio.add_chapters(
                current, work_dir / f"chapters-{downloaded.name}", chapters
            )

        final_path = (
            destination / track.album_artist / track.album / downloaded.name
        )
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
    chapters: Sequence[Chapter], audio_start_ms: int, audio_end_ms: int
) -> list[Chapter]:
    """Resolve chapters within the selected range of the source audio file."""

    for chapter in chapters:
        if not audio_start_ms <= chapter.start_ms < audio_end_ms:
            raise PipelineError(
                f"chapter at {chapter.start_ms}ms is outside the selected time range"
            )

    resolved: list[Chapter] = []
    for index, chapter in enumerate(chapters):
        next_start_ms = (
            chapters[index + 1].start_ms
            if index + 1 < len(chapters)
            else audio_end_ms
        )

        # A trimmed output starts at zero, so shift source timestamps by the
        # beginning of the selected range.
        resolved.append(
            Chapter(
                start_ms=chapter.start_ms - audio_start_ms,
                end_ms=next_start_ms - audio_start_ms,
                title=chapter.title or f"Chapter {index + 1}",
            )
        )

    return resolved
