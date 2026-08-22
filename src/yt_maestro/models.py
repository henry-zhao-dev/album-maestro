"""Domain models used by configuration and processing code."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chapter:
    """An audio chapter with timestamps relative to the processed file."""

    start_ms: int
    end_ms: int
    title: str


@dataclass(frozen=True)
class ChapterSpec:
    """A chapter declaration using a timestamp from the source recording."""

    start_ms: int
    title: str | None = None


@dataclass(frozen=True)
class TrackSpec:
    """A validated request to download and organize one recording."""

    url: str
    title: str | None = None
    artist: str | None = None
    album: str | None = None
    composer: str | None = None
    genre: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None
    chapters: tuple[ChapterSpec, ...] = ()

    def metadata(self) -> dict[str, str]:
        """Return normalized tags, including composer-based defaults."""

        metadata = {
            key: value
            for key, value in (
                ("title", self.title),
                ("artist", self.artist),
                ("album", self.album),
                ("composer", self.composer),
                ("genre", self.genre),
            )
            if value
        }

        if self.composer:
            metadata.setdefault("artist", self.composer)
            metadata.setdefault("album", self.composer.rsplit(maxsplit=1)[-1])

        if "album" in metadata:
            metadata["album_artist"] = metadata["album"]

        return metadata
