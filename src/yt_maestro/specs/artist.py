"""Loading and validation for artist specifications."""

from pathlib import Path
from typing import Any

from yt_maestro.models import Artist
from yt_maestro.specs._parsing import (
    load_json,
    optional_string,
    required_string,
)
from yt_maestro.specs._schema import validate_object


def load_artist(path: str | Path) -> Artist:
    """Load and validate one artist JSON file."""

    return parse_artist(load_json(path, label="artist"))


def parse_artist(data: Any) -> Artist:
    """Validate a decoded artist object."""

    data = validate_object(data, "artist", label="artist")
    return Artist(
        name=required_string(data, "name"),
        default_genre=optional_string(data, "default_genre"),
    )
