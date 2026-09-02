"""Domain models for the catalog and its resolved processing requests.

``Artist``, ``Album``, ``AlbumTrack``, and ``Chapter`` represent persistent JSON
configuration. ``TrackRequest`` is the fully resolved form consumed by the
download pipeline after album-level defaults have been applied.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Artist:
    """Reusable artist metadata loaded from an ``artists/<id>.json`` file."""

    name: str
    default_genre: str | None = None


@dataclass(frozen=True)
class Chapter:
    """A chapter marker within one output track.

    JSON declarations need only a start time. Chapter resolution derives the
    end from the next chapter (or the enclosing track) before embedding it.
    """

    start_ms: int
    title: str | None = None
    end_ms: int | None = None


@dataclass(frozen=True)
class AlbumTrack:
    """One output audio file declared inside an album.

    ``artist`` and ``url`` override their album-level values when present.
    Start and end timestamps refer to the selected source recording.
    """

    title: str
    artist: Artist | None = None
    url: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    chapters: tuple[Chapter, ...] = ()


@dataclass(frozen=True)
class TrackRequest:
    """A fully resolved request to produce one output audio file.

    Unlike ``AlbumTrack``, this processing model contains concrete string
    metadata and a required source URL.
    """

    url: str
    title: str
    artist: str
    album_artist: str
    album: str
    genre: str | None = None
    track_number: int | None = None
    track_total: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    chapters: tuple[Chapter, ...] = ()

    def metadata(self) -> dict[str, str]:
        """Return the audio tags resolved from album configuration."""

        metadata = {
            key: value
            for key, value in (
                ("title", self.title),
                ("artist", self.artist),
                ("album_artist", self.album_artist),
                ("album", self.album),
                ("genre", self.genre),
                ("track", self.track_number_tag()),
            )
            if value
        }
        return metadata

    def track_number_tag(self) -> str | None:
        """Return the combined track number and total metadata value."""

        if self.track_number is None or self.track_total is None:
            return None
        return f"{self.track_number}/{self.track_total}"


@dataclass(frozen=True)
class Album:
    """An ordered release with a grouping artist and optional shared defaults.

    ``album_artist`` identifies the artist under which the whole album is
    grouped. Individual tracks may credit different artists, as in a
    compilation, without changing the album artist.
    """

    title: str
    album_artist: Artist
    tracks: tuple[AlbumTrack, ...]
    genre: str | None = None
    url: str | None = None

    def requests(self) -> list[TrackRequest]:
        """Resolve catalog tracks into pipeline-ready requests.

        Resolution rules, in precedence order:

        * a track URL overrides the shared album URL;
        * a track artist overrides the album artist for that track's credit;
        * album genre overrides the selected track artist's default genre;
        * array order supplies track number and total.
        """

        total = len(self.tracks)
        requests: list[TrackRequest] = []
        for index, track in enumerate(self.tracks, start=1):
            artist = track.artist or self.album_artist
            url = track.url or self.url
            if url is None:
                raise ValueError(f"track {index} has no source URL")
            requests.append(
                TrackRequest(
                    url=url,
                    title=track.title,
                    artist=artist.name,
                    album_artist=self.album_artist.name,
                    album=self.title,
                    genre=self.genre or artist.default_genre,
                    track_number=index,
                    track_total=total,
                    start_ms=track.start_ms,
                    end_ms=track.end_ms,
                    chapters=track.chapters,
                )
            )
        return requests
