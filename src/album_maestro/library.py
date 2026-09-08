"""Application-level operations for an SQLite music library."""

from dataclasses import dataclass
from pathlib import Path

from album_maestro import database
from album_maestro.models import Album, AlbumSummary, Chapter
from album_maestro.text import optional_text, required_text


class LibraryError(ValueError):
    """Raised when a music library cannot be created or changed."""


@dataclass(frozen=True)
class Library:
    """A music library rooted at a local SQLite database and output directory."""

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
    def downloads_dir(self) -> Path:
        """Return the directory containing generated audio files."""

        return self.root / "downloads"

    def album_references(self) -> list[str]:
        """Return every album reference in database order."""

        return [album.reference for album in self.list_albums()]

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

        try:
            return database.create_album(self.database_path, album, overwrite=overwrite)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def update_album(self, reference: str, **fields: str | None) -> None:
        """Update album metadata in the SQLite catalog."""

        normalized = {
            key: (
                required_text(value, f"album {key}", error_type=LibraryError)
                if key in {"title", "genre"}
                else optional_text(value)
            )
            for key, value in fields.items()
        }
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
        """Create the library directories and SQLite database."""

        if self.database_path.exists():
            raise LibraryError(f"{self.database_path} already exists")

        self.root.mkdir(parents=True, exist_ok=True)
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        try:
            return database.initialize(self.database_path, self.name)
        except database.DatabaseError as error:
            raise LibraryError(str(error)) from error

    def validate(self) -> None:
        """Verify that the database and output directory exist."""

        if not self.database_path.is_file():
            raise LibraryError(f"database does not exist: {self.database_path}")
        if not self.downloads_dir.is_dir():
            raise LibraryError(
                f"downloads directory does not exist: {self.downloads_dir}"
            )

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
