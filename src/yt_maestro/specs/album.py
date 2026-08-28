"""Loading and validation for album specifications."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from yt_maestro.models import Album, AlbumTrack, Artist, Chapter
from yt_maestro.specs._parsing import (
    SpecError,
    artist_id,
    load_json,
    optional_string,
    optional_timestamp,
    reject_unknown_fields,
    required_string,
)
from yt_maestro.specs.artist import load_artist


def load_album(path: str | Path, artists_dir: str | Path) -> Album:
    """Load an album and resolve all artist IDs through ``artists_dir``."""

    data = load_json(path, "album")
    if not isinstance(data, Mapping):
        raise SpecError("album must be an object")

    # Resolve every reference up front so parsing can work with Artist objects
    # rather than repeatedly reading artist files track by track.
    artist_ids = {artist_id(data)}
    tracks_data = data.get("tracks")
    if isinstance(tracks_data, list):
        artist_ids.update(
            artist_id(track)
            for track in tracks_data
            if isinstance(track, Mapping) and track.get("artist") is not None
        )

    artists = {
        reference: load_artist(Path(artists_dir) / f"{reference}.json")
        for reference in artist_ids
    }
    return parse_album(data, artists)


def parse_album(data: Any, artists: Mapping[str, Artist]) -> Album:
    """Validate a decoded album object using artists keyed by catalog ID."""

    if not isinstance(data, Mapping):
        raise SpecError("album must be an object")
    reject_unknown_fields(data, {"title", "artist", "genre", "url", "tracks"}, "album")

    album_artist = _resolve_artist(data, artists)
    album_url = optional_string(data, "url")
    tracks_data = data.get("tracks")
    if not isinstance(tracks_data, list) or not tracks_data:
        raise SpecError("'tracks' must be a non-empty list")

    tracks: list[AlbumTrack] = []
    for index, track_data in enumerate(tracks_data, start=1):
        try:
            tracks.append(_parse_track(track_data, album_url, artists))
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
    data: Any, album_url: str | None, artists: Mapping[str, Artist]
) -> AlbumTrack:
    """Validate one track, retaining optional album-level overrides."""

    if not isinstance(data, Mapping):
        raise SpecError("must be an object")
    reject_unknown_fields(
        data, {"title", "artist", "url", "start", "end", "chapters"}, "track"
    )

    url = optional_string(data, "url")
    if not url and not album_url:
        raise SpecError("requires 'url' because the album has no shared 'url'")

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
        chapters=tuple(_parse_chapters(data.get("chapters", []))),
    )


def _parse_chapters(data: Any) -> list[Chapter]:
    """Validate and chronologically order source-relative chapter markers."""

    if not isinstance(data, list):
        raise SpecError("'chapters' must be a list")

    chapters: list[Chapter] = []
    for index, chapter_data in enumerate(data, start=1):
        if not isinstance(chapter_data, Mapping):
            raise SpecError(f"chapter {index} must be an object")
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

    reference = artist_id(data)
    try:
        return artists[reference]
    except KeyError as error:
        raise SpecError(f"artist {reference!r} was not resolved") from error
