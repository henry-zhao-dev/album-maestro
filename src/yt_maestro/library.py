"""Creation and representation of a declarative music library."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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

    # All configured directories must remain beneath the library root.
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


def load_config(root: str | Path = ".") -> LibraryConfig:
    """Load and validate a library manifest from a directory."""

    manifest = Path(root).expanduser().resolve() / "yt-maestro.json"
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
    name = _required_string(data, "name")
    paths = data.get("paths")
    if not isinstance(paths, Mapping):
        raise LibraryError("library manifest requires a 'paths' object")

    config = LibraryConfig(
        name=name,
        albums_dir=Path(_required_string(paths, "albums")),
        artists_dir=Path(_required_string(paths, "artists")),
        downloads_dir=Path(_required_string(paths, "downloads")),
    )
    validate_config(config)
    return config


def _required_string(data: Mapping[str, Any], key: str) -> str:
    """Read a required, non-empty manifest string."""

    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise LibraryError(f"'{key}' must be a non-empty string")
    return value.strip()
