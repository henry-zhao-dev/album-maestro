"""Creation and representation of a declarative music library."""

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ALBUMS_DIR = Path("albums")
DEFAULT_ARTISTS_DIR = Path("artists")
DEFAULT_DOWNLOADS_DIR = Path("downloads")


class LibraryError(ValueError):
    """Raised when a music library cannot be created or loaded."""


@dataclass(frozen=True)
class LibraryConfig:
    """Top-level settings for a yt-maestro music library."""

    name: str
    albums_dir: Path = DEFAULT_ALBUMS_DIR
    artists_dir: Path = DEFAULT_ARTISTS_DIR
    downloads_dir: Path = DEFAULT_DOWNLOADS_DIR

    def as_dict(self) -> dict[str, object]:
        """Return the JSON-compatible representation of this configuration."""

        return {
            "schema_version": 1,
            "kind": "library",
            "name": self.name,
            "paths": {
                "albums": self.albums_dir.as_posix(),
                "artists": self.artists_dir.as_posix(),
                "downloads": self.downloads_dir.as_posix(),
            },
        }


def validate_config(config: LibraryConfig) -> None:
    """Validate values used to initialize a library."""

    if not config.name.strip():
        raise LibraryError("library name must not be empty")

    paths = {
        "albums": config.albums_dir,
        "artists": config.artists_dir,
        "downloads": config.downloads_dir,
    }
    for label, path in paths.items():
        validate_directory_path(label, path)
    if len(set(paths.values())) != len(paths):
        raise LibraryError(
            "albums, artists, and downloads must use different directories"
        )


def validate_directory_path(label: str, path: Path) -> None:
    """Validate one directory path stored in a library configuration."""

    if not str(path) or path.is_absolute() or ".." in path.parts or path == Path("."):
        raise LibraryError(
            f"{label} must be a relative path to a directory within the library"
        )


def initialize(root: str | Path, config: LibraryConfig) -> Path:
    """Create a music library and return its manifest path."""

    validate_config(config)

    destination = Path(root).expanduser().resolve()
    manifest = destination / "yt-maestro.json"
    if manifest.exists():
        raise LibraryError(f"{manifest} already exists")

    destination.mkdir(parents=True, exist_ok=True)
    for relative_dir in (
        config.albums_dir,
        config.artists_dir,
        config.downloads_dir,
    ):
        (destination / relative_dir).mkdir(parents=True, exist_ok=True)

    manifest.write_text(json.dumps(config.as_dict(), indent=2), encoding="utf-8")
    return manifest
