"""Loading and validation for persistent artist and album specifications."""

from yt_maestro.specs._parsing import (
    SpecError,
    catalog_reference,
    load_json,
    required_string,
)
from yt_maestro.specs.catalog import load_album, load_artist

__all__ = [
    "SpecError",
    "catalog_reference",
    "load_album",
    "load_artist",
    "load_json",
    "required_string",
]
