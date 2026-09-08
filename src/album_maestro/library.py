"""Application-level operations for an SQLite music library."""

from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath, PureWindowsPath

from album_maestro import database
from album_maestro.models import Album, AlbumSummary, Chapter
from album_maestro.text import optional_text, required_text


class LibraryError(ValueError):
    """Raised when a music library cannot be created or changed."""


@dataclass(frozen=True)
class Library:
    """A music library rooted at a local SQLite database."""

    root: Path
    name: str

    def __post_init__(self) -> None:
        """Validate the name and resolve the library root."""

        root = Path(self.root).expanduser().resolve()
        object.__setattr__(self, "root", root)
        if not self.name.strip():
            raise LibraryError("library name must not be empty")

    @property
    def database_path(self) -> Path:
        """Return the SQLite database containing the catalog."""

        return self.root / "album-maestro.db"

    @property
    def sources_path(self) -> Path:
        """Return the directory containing library-relative source files."""

        return self.root / "sources"

    def album_references(self) -> list[str]:
        """Return every album reference in database order."""

        return [album.reference for album in self.list_albums()]

    def album_exists(self, reference: str) -> bool:
        """Check if an album exists in database."""

        return reference in self.album_references()

    def list_albums(self) -> list[AlbumSummary]:
        """Return album summaries stored in SQLite."""

        try:
            return database.list_albums(self.database_path)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def search_albums(
        self,
        *,
        title: str | None = None,
        artist: str | None = None,
        composer: str | None = None,
        genre: str | None = None,
    ) -> list[AlbumSummary]:
        """Search album metadata using case-insensitive substrings."""

        try:
            return database.search_albums(
                self.database_path,
                title=title,
                artist=artist,
                composer=composer,
                genre=genre,
            )
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def load_album(self, reference: str) -> Album:
        """Load one album, its tracks, and its chapters from SQLite."""

        try:
            return database.get_album(self.database_path, reference)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def create_album(
        self,
        album: Album,
        *,
        overwrite: bool = False,
    ) -> str:
        """Create or replace one complete album model in the catalog.

        Returns:
            str: The generated lowercase kebab-case album reference.
        """

        album = self._normalize_album_sources(album)
        try:
            return database.create_album(self.database_path, album, overwrite=overwrite)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def update_album(self, reference: str, **fields: str | None) -> None:
        """Update album metadata in the SQLite catalog."""

        normalized = {
            key: (
                required_text(value, label=f"album {key}", error_type=LibraryError)
                if key in {"title", "genre"}
                else optional_text(value)
            )
            for key, value in fields.items()
        }

        if "file_source" in normalized:
            normalized["file_source"] = self._normalize_file_source(
                normalized["file_source"]
            )

        try:
            database.update_album(self.database_path, reference, **normalized)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def delete_album(self, reference: str) -> None:
        """Delete one album from the catalog."""

        try:
            database.delete_album(self.database_path, reference)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def create_track(
        self,
        reference: str,
        *,
        title: str,
        artist: str | None = None,
        composer: str | None = None,
        genre: str | None = None,
        url: str | None = None,
        file_source: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        chapters: tuple[Chapter, ...] = (),
    ) -> int:
        """Append a track to an album and return its one-based position."""

        title = title.strip()
        if not title:
            raise LibraryError("track title must not be empty")
        if start_ms is not None and end_ms is not None and end_ms <= start_ms:
            raise LibraryError("track end must be later than track start")
        try:
            return database.create_track(
                self.database_path,
                reference,
                title=title,
                artist=optional_text(artist),
                composer=optional_text(composer),
                genre=optional_text(genre),
                url=optional_text(url),
                file_source=self._normalize_file_source(file_source),
                start_ms=start_ms,
                end_ms=end_ms,
                chapters=chapters,
            )
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def update_track(
        self, reference: str, position: int, **fields: str | int | None
    ) -> None:
        """Update one track's metadata or time range."""

        normalized = {
            key: optional_text(value) if isinstance(value, str) else value
            for key, value in fields.items()
        }

        if "file_source" in normalized:
            file_source = normalized["file_source"]
            if file_source is not None and not isinstance(file_source, str):
                raise LibraryError("file source must be text")
            normalized["file_source"] = self._normalize_file_source(file_source)

        try:
            database.update_track(self.database_path, reference, position, **normalized)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def delete_track(self, reference: str, position: int) -> None:
        """Delete one track from an album."""

        try:
            database.delete_track(self.database_path, reference, position)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def initialize(self) -> Path:
        """Create the library root and SQLite database."""

        if self.database_path.exists():
            raise LibraryError(f"{self.database_path} already exists")

        self.root.mkdir(parents=True, exist_ok=True)
        self.sources_path.mkdir(exist_ok=True)
        try:
            return database.initialize(self.database_path, self.name)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def validate(self) -> None:
        """Verify that the SQLite database exists."""

        if not self.database_path.is_file():
            raise LibraryError(f"database does not exist: {self.database_path}")

    def _normalize_album_sources(self, album: Album) -> Album:
        """Normalize all album and track source paths for storage."""

        return replace(
            album,
            file_source=self._normalize_file_source(album.file_source),
            tracks=tuple(
                replace(
                    track,
                    file_source=self._normalize_file_source(track.file_source),
                )
                for track in album.tracks
            ),
        )

    def _normalize_file_source(self, value: str | None) -> str | None:
        """Validate and normalize one source path relative to the library."""

        if value is None or not value.strip():
            return None

        normalized = value.strip().replace("\\", "/")
        relative = PurePosixPath(normalized)
        if relative.is_absolute() or PureWindowsPath(normalized).is_absolute():
            raise LibraryError("file source must be relative to the library")

        if relative.parts[:1] != ("sources",):
            relative = PurePosixPath("sources", *relative.parts)

        candidate = (self.root / Path(*relative.parts)).resolve(strict=False)
        sources_root = self.sources_path.resolve(strict=False)
        try:
            candidate.relative_to(sources_root)
        except ValueError as error:
            raise LibraryError(
                "file source must be inside the sources directory"
            ) from error

        if not candidate.is_file():
            raise LibraryError(f"file source does not exist: {normalized}")

        return PurePosixPath(
            *candidate.relative_to(self.root.resolve()).parts
        ).as_posix()

    @classmethod
    def load(cls, root: str | Path = ".") -> "Library":
        """Load a library from its SQLite database."""

        resolved_root = Path(root).expanduser().resolve()
        try:
            name = database.load_name(resolved_root / "album-maestro.db")
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

        music_library = cls(root=resolved_root, name=name)
        music_library.validate()
        return music_library
