"""Creation and representation of a declarative music library."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from yt_maestro.specs import required_string


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
            name=required_string(data, "name", LibraryError),
        )
        music_library.validate()
        return music_library
