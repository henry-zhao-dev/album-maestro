"""Loading and validation for persistent artist and album specifications."""

from album_maestro.specs.errors import SpecError
from album_maestro.specs.parsing import (
    optional_string,
    optional_timestamp,
    required_string,
)
from album_maestro.specs.catalog import (
    catalog_reference,
    load_album,
    load_artist,
    reference_from_text,
)
from album_maestro.specs.schema import validate_album, validate_artist
from album_maestro.specs.storage import load_json, set_json_fields, write_json

__all__ = [
    "SpecError",
    "catalog_reference",
    "load_album",
    "load_artist",
    "load_json",
    "optional_string",
    "optional_timestamp",
    "required_string",
    "reference_from_text",
    "set_json_fields",
    "validate_album",
    "validate_artist",
    "write_json",
]
