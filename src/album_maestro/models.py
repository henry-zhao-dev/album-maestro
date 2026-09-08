"""Domain models for catalog specifications and resolved media requests."""

from dataclasses import dataclass

from album_maestro.text import optional_text, required_text

VARIOUS_ARTISTS = "Various Artists"


@dataclass(frozen=True)
class AlbumSummary:
    """The catalog fields needed to display an album in a list."""

    id: int
    reference: str
    title: str
    artist: str | None
    composer: str | None
    genre: str
    track_count: int


@dataclass(frozen=True)
class Chapter:
    """A chapter marker within one output track."""

    start_ms: int
    title: str | None = None
    end_ms: int | None = None

    def __post_init__(self) -> None:
        """Normalize chapter text and validate its time range."""

        if self.start_ms < 0:
            raise ValueError("chapter start must not be negative")
        if self.end_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError("chapter end must be later than chapter start")
        object.__setattr__(self, "title", optional_text(self.title))


@dataclass(frozen=True)
class AlbumTrack:
    """One output audio file declared inside an album.

    Metadata values override the corresponding album-level defaults when
    present. The file source follows the same album-default and track-override
    pattern as the URL. Start and end timestamps refer to the selected source
    recording.
    """

    title: str
    artist: str | None = None
    url: str | None = None
    file_source: str | None = None
    composer: str | None = None
    genre: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    chapters: tuple[Chapter, ...] = ()

    def __post_init__(self) -> None:
        """Normalize track text and validate its time range."""

        object.__setattr__(
            self, "title", required_text(self.title, label="track title")
        )
        object.__setattr__(self, "artist", optional_text(self.artist))
        object.__setattr__(self, "url", optional_text(self.url))
        object.__setattr__(self, "file_source", optional_text(self.file_source))
        object.__setattr__(self, "composer", optional_text(self.composer))
        object.__setattr__(self, "genre", optional_text(self.genre))
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms <= self.start_ms
        ):
            raise ValueError("track end must be later than track start")
        object.__setattr__(self, "chapters", tuple(self.chapters))


@dataclass(frozen=True)
class TrackRequest:
    """A fully resolved track request for source audio processing."""

    url: str
    title: str
    artist: str
    album_artist: str
    album: str
    composer: str | None = None
    genre: str | None = None
    track_number: int | None = None
    track_total: int | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    chapters: tuple[Chapter, ...] = ()

    def metadata(self) -> dict[str, str]:
        """Return standard audio tags resolved from album configuration."""

        metadata = {
            key: value
            for key, value in (
                ("title", self.title),
                ("artist", self.artist),
                ("album_artist", self.album_artist),
                ("album", self.album),
                ("composer", self.composer),
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
    """An ordered release with album-level metadata defaults.

    The album-level ``artist`` is the default track artist and output
    ``album_artist``. It may be absent for compilations. In that case both
    output artist fields use ``Various Artists`` unless a track overrides its
    own artist. Composer is an independent optional credit and never fills in
    for artist. Genre is explicit and inherited by tracks unless overridden.
    """

    title: str
    artist: str | None
    tracks: tuple[AlbumTrack, ...]
    genre: str
    composer: str | None = None
    url: str | None = None
    file_source: str | None = None

    def __post_init__(self) -> None:
        """Normalize text and validate invariants for one album model."""

        object.__setattr__(
            self, "title", required_text(self.title, label="album title")
        )
        object.__setattr__(self, "artist", optional_text(self.artist))
        object.__setattr__(self, "composer", optional_text(self.composer))
        object.__setattr__(
            self, "genre", required_text(self.genre, label="album genre")
        )
        object.__setattr__(self, "url", optional_text(self.url))
        object.__setattr__(self, "file_source", optional_text(self.file_source))
        object.__setattr__(self, "tracks", tuple(self.tracks))

    def resolved_album_artist(self) -> str:
        """Return the output album artist, defaulting compilations."""

        return self.artist or VARIOUS_ARTISTS

    def requests(self) -> list[TrackRequest]:
        """Apply album defaults and per-track overrides."""

        total = len(self.tracks)
        album_artist = self.resolved_album_artist()
        requests: list[TrackRequest] = []
        for index, track in enumerate(self.tracks, start=1):
            url = track.url or self.url
            if url is None:
                raise ValueError(f"track {index} has no reference URL")
            requests.append(
                TrackRequest(
                    url=url,
                    title=track.title,
                    artist=track.artist or album_artist,
                    album_artist=album_artist,
                    album=self.title,
                    composer=track.composer or self.composer,
                    genre=track.genre or self.genre,
                    track_number=index,
                    track_total=total,
                    start_ms=track.start_ms,
                    end_ms=track.end_ms,
                    chapters=track.chapters,
                )
            )
        return requests
