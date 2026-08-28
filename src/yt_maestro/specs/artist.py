"""Loading and validation for artist specifications."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from yt_maestro.models import Artist
from yt_maestro.specs._parsing import (
    SpecError,
    load_json,
    optional_string,
    reject_unknown_fields,
    required_string,
)


def load_artist(path: str | Path) -> Artist:
    """Load and validate one artist JSON file."""

    return parse_artist(load_json(path, "artist"))


def parse_artist(data: Any) -> Artist:
    """Validate a decoded artist object."""

    if not isinstance(data, Mapping):
        raise SpecError("artist must be an object")
    reject_unknown_fields(data, {"name", "default_genre"}, "artist")
    return Artist(
        name=required_string(data, "name"),
        default_genre=optional_string(data, "default_genre"),
    )
