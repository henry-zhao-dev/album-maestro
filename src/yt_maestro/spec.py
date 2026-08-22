"""Loading and validation for declarative track specifications."""

import json
import math
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from yt_maestro.models import Chapter, ChapterSpec, TrackSpec


class SpecError(ValueError):
    """Raised when a specification cannot be parsed or resolved."""


def load_specs(path: str | Path) -> list[TrackSpec]:
    """Load and validate every track in a JSON specification file."""

    try:
        with Path(path).open(encoding="utf-8") as spec_file:
            data = json.load(spec_file)
    except OSError as error:
        raise SpecError(f"cannot read specification: {error}") from error
    except json.JSONDecodeError as error:
        raise SpecError(f"invalid JSON at line {error.lineno}: {error.msg}") from error

    return parse_specs(data)


def parse_specs(data: Any) -> list[TrackSpec]:
    """Validate a decoded JSON value as a list of track specifications."""

    if not isinstance(data, list):
        raise SpecError("the top-level specification must be a list")

    parsed: list[TrackSpec] = []
    for index, item in enumerate(data, start=1):
        try:
            parsed.append(parse_track(item))
        except SpecError as error:
            raise SpecError(f"track {index}: {error}") from error
    return parsed


def parse_track(data: Any) -> TrackSpec:
    """Validate and normalize one decoded track object."""

    if not isinstance(data, Mapping):
        raise SpecError("must be an object")

    url = _optional_string(data, "url")
    if not url:
        raise SpecError("'url' must be a non-empty string")

    start_ms = _optional_timestamp(data, "start")
    end_ms = _optional_timestamp(data, "end")
    if start_ms is not None and end_ms is not None and end_ms <= start_ms:
        raise SpecError("'end' must be later than 'start'")

    chapters_data = data.get("chapters", [])
    if not isinstance(chapters_data, list):
        raise SpecError("'chapters' must be a list")

    chapters: list[ChapterSpec] = []
    for index, chapter_data in enumerate(chapters_data, start=1):
        if not isinstance(chapter_data, Mapping):
            raise SpecError(f"chapter {index} must be an object")
        chapter_start = _optional_timestamp(chapter_data, "start")
        if chapter_start is None:
            raise SpecError(f"chapter {index} requires 'start'")
        chapters.append(
            ChapterSpec(
                start_ms=chapter_start,
                title=_optional_string(chapter_data, "title"),
            )
        )

    chapters.sort(key=lambda chapter: chapter.start_ms)
    if len({chapter.start_ms for chapter in chapters}) != len(chapters):
        raise SpecError("chapter start times must be unique")

    return TrackSpec(
        url=url,
        title=_optional_string(data, "title"),
        artist=_optional_string(data, "artist"),
        album=_optional_string(data, "album"),
        composer=_optional_string(data, "composer"),
        genre=_optional_string(data, "genre"),
        start_ms=start_ms,
        end_ms=end_ms,
        chapters=tuple(chapters),
    )


def resolve_time_range(track: TrackSpec, duration_ms: int) -> tuple[int, int]:
    """Resolve optional trim bounds against the downloaded file duration."""

    if duration_ms <= 0:
        raise SpecError("downloaded audio has no valid duration")

    start_ms = track.start_ms if track.start_ms is not None else 0
    end_ms = track.end_ms if track.end_ms is not None else duration_ms
    if not 0 <= start_ms < end_ms <= duration_ms:
        raise SpecError(
            f"time range {start_ms}ms..{end_ms}ms is outside "
            f"the {duration_ms}ms recording"
        )
    return start_ms, end_ms


def resolve_chapters(
    chapter_specs: Sequence[ChapterSpec], start_ms: int, end_ms: int
) -> list[Chapter]:
    """Convert source-relative chapter declarations to output timestamps."""

    for chapter in chapter_specs:
        if not start_ms <= chapter.start_ms < end_ms:
            raise SpecError(
                f"chapter at {chapter.start_ms}ms is outside the selected time range"
            )

    return [
        Chapter(
            start_ms=chapter.start_ms - start_ms,
            end_ms=(
                chapter_specs[index + 1].start_ms
                if index + 1 < len(chapter_specs)
                else end_ms
            )
            - start_ms,
            title=chapter.title or f"Chapter {index + 1}",
        )
        for index, chapter in enumerate(chapter_specs)
    ]


def parse_timestamp(value: str) -> int:
    """Convert ``hh:mm:ss``, ``mm:ss``, or seconds into milliseconds."""

    parts = value.split(":")
    if not 1 <= len(parts) <= 3 or any(not part for part in parts):
        raise SpecError(f"invalid timestamp: {value!r}")

    try:
        numbers = [float(part) for part in parts]
    except ValueError as error:
        raise SpecError(f"invalid timestamp: {value!r}") from error

    if any(not math.isfinite(number) or number < 0 for number in numbers):
        raise SpecError(f"invalid timestamp: {value!r}")

    while len(numbers) < 3:
        numbers.insert(0, 0.0)
    hours, minutes, seconds = numbers
    return round((hours * 3600 + minutes * 60 + seconds) * 1000)


def _optional_string(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SpecError(f"'{key}' must be a string")
    return value.strip() or None


def _optional_timestamp(data: Mapping[str, Any], key: str) -> int | None:
    value = _optional_string(data, key)
    return parse_timestamp(value) if value is not None else None
