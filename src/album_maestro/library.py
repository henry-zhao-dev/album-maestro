"""Creation and representation of a declarative music library."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from album_maestro import specs
from album_maestro.models import Album


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

        return {"kind": "library", "name": self.name}

    @property
    def albums_dir(self) -> Path:
        """Return the directory containing album declarations."""

        return self.root / "albums"

    @property
    def downloads_dir(self) -> Path:
        """Return the directory containing generated audio files."""

        return self.root / "downloads"

    @property
    def manifest(self) -> Path:
        """Return the library manifest path."""

        return self.root / "album-maestro.json"

    def album_references(self) -> list[str]:
        """Return every album reference in filename order."""

        return [path.stem for path in sorted(self.albums_dir.glob("*.json"))]

    def load_album(self, reference: str) -> Album:
        """Load an album by its filename reference."""

        filename = _catalog_filename(reference, label="album")
        return specs.load_album(self.albums_dir / filename)

    def create_album(
        self,
        title: str,
        artist: str | None,
        *,
        composer: str | None = None,
        genre: str,
        shared_url: str | None = None,
    ) -> Path:
        """Create an empty, self-contained album declaration."""

        title = title.strip()
        artist = _optional_text(artist)
        composer = _optional_text(composer)
        genre = genre.strip()
        shared_url = _optional_text(shared_url)
        if not genre:
            raise LibraryError("album genre must not be empty")

        try:
            reference = specs.reference_from_text(title, label="album title")
        except ValueError as error:
            raise LibraryError(str(error)) from error

        album_path = self.albums_dir / f"{reference}.json"
        if album_path.exists():
            raise LibraryError(f"album already exists: {album_path}")

        album_data: dict[str, object] = {
            "title": title,
            "artist": artist,
            "genre": genre,
            "tracks": [],
        }
        if composer:
            album_data["composer"] = composer
        if shared_url:
            album_data["url"] = shared_url

        try:
            specs.write_json(album_path, album_data)
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error
        return album_path

    def initialize(self) -> Path:
        """Create the library directories and manifest."""

        if self.manifest.exists():
            raise LibraryError(f"{self.manifest} already exists")

        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (self.albums_dir, self.downloads_dir):
            directory.mkdir(parents=True, exist_ok=True)
        self.manifest.write_text(json.dumps(self.as_dict(), indent=2), encoding="utf-8")
        return self.manifest

    def validate(self) -> None:
        """Verify that the fixed library directory structure exists."""

        for label, directory in {
            "albums": self.albums_dir,
            "downloads": self.downloads_dir,
        }.items():
            if not directory.is_dir():
                raise LibraryError(f"{label} directory does not exist: {directory}")

    @classmethod
    def load(cls, root: str | Path = ".") -> "Library":
        """Load a library from its manifest."""

        resolved_root = Path(root).expanduser().resolve()
        manifest = resolved_root / "album-maestro.json"
        try:
            data = specs.load_json(manifest, label="library manifest")
        except specs.SpecError as error:
            raise LibraryError(str(error)) from error

        if not isinstance(data, Mapping) or data.get("kind") != "library":
            raise LibraryError("album-maestro.json is not a library manifest")

        music_library = cls(
            root=resolved_root,
            name=specs.required_string(data, "name", LibraryError),
        )
        music_library.validate()
        return music_library


def _catalog_filename(reference: str, *, label: str) -> str:
    """Validate an album reference and return its JSON filename."""

    path = Path(reference)
    if path.name != reference or reference in {"", ".", ".."}:
        raise specs.SpecError(f"{label} reference must be a filename, not a path")
    reference_without_ext = reference.removesuffix(".json")
    canonical_reference = specs.catalog_reference(reference_without_ext, label=label)
    return f"{canonical_reference}.json"


def _optional_text(value: str | None) -> str | None:
    """Normalize optional text to ``None`` when blank."""

    return value.strip() if value and value.strip() else None
