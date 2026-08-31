"""Loading and validation for album specifications."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from yt_maestro.models import Album, AlbumTrack, Artist, Chapter
from yt_maestro.specs._parsing import (
    SpecError,
    artist_reference,
    load_json,
    optional_string,
    optional_timestamp,
    required_string,
)
from yt_maestro.specs._schema import validate_object
from yt_maestro.specs.artist import load_artist


def load_album(path: str | Path, artists_dir: str | Path) -> Album:
    """Load an album and resolve all artist IDs through ``artists_dir``."""

    data = validate_object(load_json(path, label="album"), "album", label="album")

    # Resolve every reference up front so parsing can work with Artist objects
    # rather than repeatedly reading artist files track by track.
    artist_references = {artist_reference(data)}
    tracks_data = data.get("tracks")
    if isinstance(tracks_data, list):
        artist_references.update(
            artist_reference(track)
            for track in tracks_data
            if isinstance(track, Mapping) and track.get("artist") is not None
        )

    artists = {
        reference: load_artist(Path(artists_dir) / f"{reference}.json")
        for reference in artist_references
    }
    return _parse_album(data, artists)


def parse_album(data: Any, artists: Mapping[str, Artist]) -> Album:
    """Validate a decoded album object using artists keyed by catalog ID."""

    data = validate_object(data, "album", label="album")
    return _parse_album(data, artists)


def _parse_album(data: Mapping[str, Any], artists: Mapping[str, Artist]) -> Album:
    """Convert a schema-valid album object into the domain model."""

    album_artist = _resolve_artist(data, artists)
    album_url = optional_string(data, "url")
    tracks_data = cast(list[Mapping[str, Any]], data["tracks"])

    tracks: list[AlbumTrack] = []
    for index, track_data in enumerate(tracks_data, start=1):
        try:
            tracks.append(_parse_track(track_data, artists))
        except SpecError as error:
            raise SpecError(f"track {index}: {error}") from error

    return Album(
        title=required_string(data, "title"),
        album_artist=album_artist,
        tracks=tuple(tracks),
        genre=optional_string(data, "genre"),
        url=album_url,
    )


def _parse_track(
    data: Mapping[str, Any], artists: Mapping[str, Artist]
) -> AlbumTrack:
    """Convert one schema-valid track, retaining album-level overrides."""

    url = optional_string(data, "url")
    start_ms = optional_timestamp(data, "start")
    end_ms = optional_timestamp(data, "end")
    if start_ms is not None and end_ms is not None and end_ms <= start_ms:
        raise SpecError("'end' must be later than 'start'")

    return AlbumTrack(
        title=required_string(data, "title"),
        artist=(
            _resolve_artist(data, artists) if data.get("artist") is not None else None
        ),
        url=url,
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

    # JSON order is not required to be chronological, but chapter output is.
    chapters.sort(key=lambda chapter: chapter.start_ms)
    if len({chapter.start_ms for chapter in chapters}) != len(chapters):
        raise SpecError("chapter start times must be unique")
    return chapters


def _resolve_artist(data: Mapping[str, Any], artists: Mapping[str, Artist]) -> Artist:
    """Replace an artist ID with its previously loaded catalog entry."""

    reference = artist_reference(data)
    try:
        return artists[reference]
    except KeyError as error:
        raise SpecError(f"artist {reference!r} was not resolved") from error
