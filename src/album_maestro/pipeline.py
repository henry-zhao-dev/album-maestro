"""Build track files from resolved catalog models and source audio."""

import logging
import shutil
from collections.abc import Sequence
from pathlib import Path

from album_maestro import audio
from album_maestro.models import Chapter, TrackRequest

logger = logging.getLogger(__name__)


class PipelineError(ValueError):
    """Raised when catalog data cannot be transformed into output audio."""


def create_track(
    track: TrackRequest,
    source: Path,
    destination: Path,
    work_dir: Path,
) -> Path:
    """Create one track from a source audio file."""

    track_source = work_dir / f"{track.title}{source.suffix}"
    shutil.copy2(source, track_source)

    duration_ms = audio.audio_duration_ms(track_source)
    audio_start_ms, audio_end_ms = _resolve_time_range(track, duration_ms)
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
        chapters = _resolve_chapters(track.chapters, audio_start_ms, audio_end_ms)
        current = audio.add_chapters(
            current, work_dir / f"chapters-{track_source.name}", chapters
        )

    final_path = _track_output_path(track, destination, track_source.suffix)
    final_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(current, final_path)
    return final_path


def _track_output_path(
    track: TrackRequest,
    destination: Path,
    suffix: str,
) -> Path:
    """Return the final library path for a track."""

    destination = destination.resolve()
    components = (
        _safe_path_component(track.album_artist, label="album artist"),
        _safe_path_component(track.album, label="album title"),
        _safe_path_component(track.title, label="track title") + suffix,
    )
    output = destination.joinpath(*components)
    try:
        output.resolve().relative_to(destination)
    except ValueError as error:
        raise PipelineError(
            "track output path escapes the destination directory"
        ) from error
    return output


def _safe_path_component(value: str, *, label: str) -> str:
    """Validate one catalog value before using it as a path component."""

    if not value or value in {".", ".."}:
        raise PipelineError(f"{label} cannot be used as an output path component")
    if any(character in value for character in ("/", "\\", "\x00")):
        raise PipelineError(f"{label} contains a path separator or null character")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise PipelineError(f"{label} contains a control character")
    if Path(value).is_absolute():
        raise PipelineError(f"{label} must be a relative path component")
    return value


def _resolve_time_range(track: TrackRequest, duration_ms: int) -> tuple[int, int]:
    """Resolve optional trim bounds against the source file duration."""

    if duration_ms <= 0:
        raise PipelineError("source audio has no valid duration")

    start_ms = track.start_ms if track.start_ms is not None else 0
    end_ms = track.end_ms if track.end_ms is not None else duration_ms
    if not 0 <= start_ms < end_ms <= duration_ms:
        raise PipelineError(
            f"time range {start_ms}ms..{end_ms}ms is outside "
            f"the {duration_ms}ms recording"
        )
    return start_ms, end_ms


def _resolve_chapters(
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
            chapters[index + 1].start_ms if index + 1 < len(chapters) else audio_end_ms
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
