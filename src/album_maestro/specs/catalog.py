"""Load and parse declarative album specifications."""

import re
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from album_maestro.models import Album, AlbumTrack, Chapter
from album_maestro.specs.errors import SpecError
from album_maestro.specs.parsing import (
    format_timestamp,
    optional_string,
    optional_timestamp,
    required_string,
)
from album_maestro.specs.schema import validate_album
from album_maestro.specs.storage import load_json


def catalog_reference(value: str, *, label: str) -> str:
    """Validate a lowercase kebab-case filename reference."""

    if not all(
        part and part.isascii() and part.isalnum() and part == part.lower()
        for part in value.split("-")
    ):
        raise SpecError(
            f"{label} reference must be lowercase kebab-case, such as 'album-name'"
        )
    return value


def reference_from_text(value: str, *, label: str) -> str:
    """Convert display text to a canonical filename reference."""

    normalized = re.sub(r"['’ʼ]", "", unicodedata.normalize("NFKD", value))
    normalized = normalized.encode("ascii", "ignore").decode()
    reference = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
    if not reference:
        raise ValueError(f"{label} cannot form a catalog reference")
    return reference


def load_album(path: str | Path) -> Album:
    """Load and validate one self-contained album specification."""

    return _parse_album(load_json(path, label="album"))


def dump_album(album: Album) -> dict[str, object]:
    """Convert one album model to the JSON specification shape."""

    data: dict[str, object] = {"title": album.title}
    if album.artist is not None:
        data["artist"] = album.artist
    if album.composer is not None:
        data["composer"] = album.composer
    data["genre"] = album.genre
    if album.url is not None:
        data["url"] = album.url
    if album.file_source is not None:
        data["file_source"] = album.file_source
    data["tracks"] = [_track_data(track) for track in album.tracks]
    return data


def _parse_album(data: Any) -> Album:
    """Convert one schema-valid album object into the domain model."""

    data = validate_album(data)
    tracks_data = cast(list[Mapping[str, Any]], data["tracks"])
    tracks: list[AlbumTrack] = []
    for index, track_data in enumerate(tracks_data, start=1):
        try:
            tracks.append(_parse_track(track_data))
        except SpecError as error:
            raise SpecError(f"track {index}: {error}") from error

    return Album(
        title=required_string(data, "title"),
        artist=optional_string(data, "artist"),
        tracks=tuple(tracks),
        composer=optional_string(data, "composer"),
        genre=required_string(data, "genre"),
        url=optional_string(data, "url"),
        file_source=optional_string(data, "file_source"),
    )


def _parse_track(data: Mapping[str, Any]) -> AlbumTrack:
    """Convert one schema-valid track, retaining album-level overrides."""

    start_ms = optional_timestamp(data, "start")
    end_ms = optional_timestamp(data, "end")
    if start_ms is not None and end_ms is not None and end_ms <= start_ms:
        raise SpecError("'end' must be later than 'start'")

    return AlbumTrack(
        title=required_string(data, "title"),
        artist=optional_string(data, "artist"),
        url=optional_string(data, "url"),
        file_source=optional_string(data, "file_source"),
        composer=optional_string(data, "composer"),
        genre=optional_string(data, "genre"),
        start_ms=start_ms,
        end_ms=end_ms,
        chapters=tuple(
            _parse_chapters(cast(list[Mapping[str, Any]], data.get("chapters", [])))
        ),
    )


def _parse_chapters(data: list[Mapping[str, Any]]) -> list[Chapter]:
    """Convert and chronologically order schema-valid chapter markers."""

    chapters: list[Chapter] = []
    for index, chapter_data in enumerate(data, start=1):
        chapter_start = optional_timestamp(chapter_data, "start")
        if chapter_start is None:
            raise SpecError(f"chapter {index} requires 'start'")
        chapters.append(
            Chapter(
                start_ms=chapter_start,
                title=optional_string(chapter_data, "title"),
            )
        )

    chapters.sort(key=lambda chapter: chapter.start_ms)
    if len({chapter.start_ms for chapter in chapters}) != len(chapters):
        raise SpecError("chapter start times must be unique")
    return chapters


def _track_data(track: AlbumTrack) -> dict[str, object]:
    """Convert one album track to its JSON specification shape."""

    data: dict[str, object] = {"title": track.title}
    for key, value in (
        ("artist", track.artist),
        ("url", track.url),
        ("file_source", track.file_source),
        ("composer", track.composer),
        ("genre", track.genre),
    ):
        if value is not None:
            data[key] = value
    if track.start_ms is not None:
        data["start"] = format_timestamp(track.start_ms)
    if track.end_ms is not None:
        data["end"] = format_timestamp(track.end_ms)
    if track.chapters:
        data["chapters"] = [_chapter_data(chapter) for chapter in track.chapters]
    return data


def _chapter_data(chapter: Chapter) -> dict[str, object]:
    """Convert one chapter marker to its JSON specification shape."""

    data: dict[str, object] = {"start": format_timestamp(chapter.start_ms)}
    if chapter.title is not None:
        data["title"] = chapter.title
    return data
