"""Loading and validation for persistent album specifications."""

from album_maestro.specs.errors import SpecError
from album_maestro.specs.parsing import (
    optional_string,
    optional_timestamp,
    required_string,
    parse_timestamp,
)
from album_maestro.specs.catalog import (
    catalog_reference,
    load_album,
    reference_from_text,
)
from album_maestro.specs.schema import validate_album
from album_maestro.specs.storage import load_json, set_json_fields, write_json

__all__ = [
    "SpecError",
    "catalog_reference",
    "load_album",
    "load_json",
    "optional_string",
    "optional_timestamp",
    "parse_timestamp",
    "required_string",
    "reference_from_text",
    "set_json_fields",
    "validate_album",
    "write_json",
]
