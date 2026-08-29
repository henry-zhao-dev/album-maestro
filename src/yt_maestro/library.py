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

    def load_album(self, reference: str) -> Album:
        """Load an album and resolve its artist references."""

        filename = _catalog_filename(reference, "album")
        return specs.load_album(self.albums_dir / filename, self.artists_dir)

    def load_artist(self, reference: str) -> Artist:
        """Load an artist by its catalog reference."""

        filename = _catalog_filename(reference, "artist")
        return specs.load_artist(self.artists_dir / filename)

    def initialize(self) -> Path:
        """Create the library directories and manifest."""

        if self.manifest.exists():
            raise LibraryError(f"{self.manifest} already exists")

        self.root.mkdir(parents=True, exist_ok=True)
        for directory in (self.albums_dir, self.artists_dir, self.downloads_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.manifest.write_text(
            json.dumps(self.as_dict(), indent=2), encoding="utf-8"
        )
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
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except OSError as error:
            raise LibraryError(f"cannot read library manifest: {error}") from error
        except json.JSONDecodeError as error:
            raise LibraryError(
                f"invalid library manifest JSON at line {error.lineno}: {error.msg}"
            ) from error

        if not isinstance(data, Mapping) or data.get("kind") != "library":
            raise LibraryError("yt-maestro.json is not a library manifest")

        music_library = cls(
            root=resolved_root,
            name=specs.required_string(data, "name", LibraryError),
        )
        music_library.validate()
        return music_library


def _catalog_filename(reference: str, label: str) -> str:
    """Validate a catalog reference and return its JSON filename."""

    path = Path(reference)
    if path.name != reference or reference in {"", ".", ".."}:
        raise specs.SpecError(f"{label} reference must be a filename, not a path")

    reference_without_extension = reference.removesuffix(".json")
    canonical_reference = specs.catalog_reference(
        reference_without_extension, label=label
    )
    return f"{canonical_reference}.json"
