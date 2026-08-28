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
    """Download each unique source once and create its requested tracks."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    sources: dict[str, Path | None] = {}

    with tempfile.TemporaryDirectory(
        prefix=".yt-maestro-", dir=destination
    ) as temp:
        temp_dir = Path(temp)

        for index, track in enumerate(tracks, start=1):
            if track.url not in sources:
                source_dir = temp_dir / f"source-{len(sources) + 1}"
                source_dir.mkdir()
                sources[track.url] = downloader.download_audio(
                    track.url, source_dir
                )

            source = sources[track.url]
            if source is None:
                continue

            logging.info("Creating track %s of %s", index, len(tracks))
            work_dir = temp_dir / f"track-{index}"
            work_dir.mkdir()
            try:
                output = _create_track(track, source, destination, work_dir)
            except PipelineError as error:
                logging.error("cannot create track %s: %s", index, error)
                continue
            outputs.append(output)

    return outputs


def download_track(track: TrackRequest, output_dir: str | Path = ".") -> Path | None:
    """Download, transform, and organize one validated track."""

    outputs = download_tracks((track,), output_dir)
    return outputs[0] if outputs else None


def _create_track(
    track: TrackRequest,
    source: Path,
    destination: Path,
    work_dir: Path,
) -> Path:
    """Create one track from an already downloaded source file."""

    track_source = work_dir / f"{track.title}{source.suffix}"
    shutil.copy2(source, track_source)

    duration_ms = audio.audio_duration_ms(track_source)
    audio_start_ms, audio_end_ms = resolve_time_range(track, duration_ms)
    # Each processing stage consumes the file produced by the previous one.
    current = str(track_source)

    if track.start_ms is not None or track.end_ms is not None:
        current = audio.trim_audio(
            current,
            work_dir / f"trim-{track_source.name}",
            audio_start_ms,
            audio_end_ms,
        )

    metadata = track.metadata()
    current = audio.add_metadata(
        current, work_dir / f"metadata-{track_source.name}", metadata
    )

    if track.chapters:
        chapters = resolve_chapters(
            track.chapters, audio_start_ms, audio_end_ms
        )
        current = audio.add_chapters(
            current, work_dir / f"chapters-{track_source.name}", chapters
        )

    final_path = (
        destination / track.album_artist / track.album / track_source.name
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
