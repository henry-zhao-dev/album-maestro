"""Creation and representation of a declarative music library."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_maestro import specs
from yt_maestro.models import Album, Artist


class LibraryError(ValueError):
    """Raised when a music library cannot be created or loaded."""


@dataclass(frozen=True)
class Library:
    """A music library rooted at a fixed catalog directory layout."""

    root: Path
    name: str

    def __post_init__(self) -> None:
        """Validate the name and resolve the library root."""

        root = Path(self.root).expanduser().resolve()
        object.__setattr__(self, "root", root)

        if not self.name.strip():
            raise LibraryError("library name must not be empty")

    def as_dict(self) -> dict[str, object]:
        """Return the portable JSON representation stored in the manifest."""

        return {
            "kind": "library",
            "name": self.name,
        }

    @property
    def albums_dir(self) -> Path:
        """Return the directory containing album declarations."""

        return self.root / "albums"

    @property
    def artists_dir(self) -> Path:
        """Return the directory containing artist declarations."""

        return self.root / "artists"

    @property
    def downloads_dir(self) -> Path:
        """Return the directory containing generated audio files."""

        return self.root / "downloads"

    @property
    def manifest(self) -> Path:
        """Return the library manifest path."""

        return self.root / "yt-maestro.json"

    def album_references(self) -> list[str]:
        """Return every album reference in filename order."""

        return [path.stem for path in sorted(self.albums_dir.glob("*.json"))]

    def artist_references(self) -> list[str]:
        """Return every artist reference in filename order."""

        return [path.stem for path in sorted(self.artists_dir.glob("*.json"))]

    def load_album(self, reference: str) -> Album:
        """Load an album and resolve its artist references."""

        filename = _catalog_filename(reference, label="album")
        return specs.load_album(self.albums_dir / filename, self.artists_dir)

    def load_artist(self, reference: str) -> Artist:
        """Load an artist by its catalog reference."""

        filename = _catalog_filename(reference, label="artist")
        return specs.load_artist(self.artists_dir / filename)

    def create_artist(self, name: str, default_genre: str | None = None) -> str:
        """Create an artist declaration and return its canonical reference.

        Blank optional genres are omitted from the declaration.
        """

        name = name.strip()
        try:
            reference = specs.reference_from_text(name, label="artist name")
        except ValueError as error:
            raise LibraryError(str(error)) from error

        artist_path = self.artists_dir / f"{reference}.json"
        if artist_path.exists():
            raise LibraryError(f"artist reference already exists: {reference}")

        artist_data: dict[str, object] = {"name": name}
        genre = _optional_text(default_genre)
        if genre:
            artist_data["default_genre"] = genre
        try:
            specs.write_json(artist_path, artist_data)
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error
        return reference

    def update_artist_default_genre(self, reference: str, genre: str) -> None:
        """Set the default genre on an existing artist declaration."""

        genre = genre.strip()
        if not genre:
            raise LibraryError("artist default genre must not be empty")

        try:
            filename = _catalog_filename(reference, label="artist")
            specs.set_json_fields(
                self.artists_dir / filename,
                {"default_genre": genre},
                label="artist",
            )
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error

    def create_album(
        self,
        title: str,
        artist_reference: str,
        *,
        genre: str | None = None,
        shared_url: str | None = None,
    ) -> Path:
        """Create an empty album declaration and return its path.

        A genre matching the artist's default is omitted as redundant. Blank
        optional values are omitted from the declaration.
        """

        title = title.strip()
        try:
            reference = specs.reference_from_text(title, label="album title")
            artist_filename = _catalog_filename(artist_reference, label="artist")
            artist = specs.load_artist(self.artists_dir / artist_filename)
        except ValueError as error:
            raise LibraryError(str(error)) from error

        album_path = self.albums_dir / f"{reference}.json"
        if album_path.exists():
            raise LibraryError(f"album already exists: {album_path}")

        album_data: dict[str, object] = {
            "title": title,
            "artist": artist_filename.removesuffix(".json"),
            "tracks": [],
        }
        genre = _optional_text(genre)
        if genre and genre != artist.default_genre:
            album_data["genre"] = genre
        shared_url = _optional_text(shared_url)
        if shared_url:
            album_data["url"] = shared_url

        try:
            specs.write_json(album_path, album_data)
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error
        return album_path

    def artist_matches(self, name: str) -> list[tuple[str, Artist]]:
        """Return case-insensitive substring matches as reference/artist pairs."""

        name = name.strip()
        if not name:
            raise LibraryError("artist name must not be empty")

        query = name.casefold()
        matches: list[tuple[str, Artist]] = []
        for reference in self.artist_references():
            artist = self.load_artist(reference)
            if query in artist.name.casefold():
                matches.append((reference, artist))

        return matches

    def initialize(self) -> Path:
        """Create the library directories and manifest."""

        if self.manifest.exists():
            raise LibraryError(f"{self.manifest} already exists")

        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (self.albums_dir, self.artists_dir, self.downloads_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.manifest.write_text(json.dumps(self.as_dict(), indent=2), encoding="utf-8")
        return self.manifest

    def validate(self) -> None:
        """Verify that the fixed library directory structure exists."""

        directories = {
            "albums": self.albums_dir,
            "artists": self.artists_dir,
            "downloads": self.downloads_dir,
        }
        for label, directory in directories.items():
            if not directory.is_dir():
                raise LibraryError(f"{label} directory does not exist: {directory}")

    @classmethod
    def load(cls, root: str | Path = ".") -> "Library":
        """Load a library from its manifest."""

        resolved_root = Path(root).expanduser().resolve()
        manifest = resolved_root / "yt-maestro.json"

        try:
            data = specs.load_json(manifest, label="library manifest")
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error

        if not isinstance(data, Mapping) or data.get("kind") != "library":
            raise LibraryError("yt-maestro.json is not a library manifest")

        music_library = cls(
            root=resolved_root,
            name=specs.required_string(data, "name", LibraryError),
        )
        music_library.validate()
        return music_library


def _catalog_filename(reference: str, *, label: str) -> str:
    """Validate a catalog reference and return its JSON filename."""

    path = Path(reference)
    if path.name != reference or reference in {"", ".", ".."}:
        raise specs.SpecError(f"{label} reference must be a filename, not a path")

    reference_without_ext = reference.removesuffix(".json")
    canonical_reference = specs.catalog_reference(reference_without_ext, label=label)
    return f"{canonical_reference}.json"


def _optional_text(value: str | None) -> str | None:
    """Normalize an optional text value to ``None`` when blank."""

    return value.strip() if value and value.strip() else None
