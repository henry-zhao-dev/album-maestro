"""Loading and validation for persistent artist and album specifications."""

from yt_maestro.specs.errors import SpecError
from yt_maestro.specs.parsing import (
    optional_string,
    optional_timestamp,
    required_string,
)
from yt_maestro.specs.catalog import (
    catalog_reference,
    load_album,
    load_artist,
    reference_from_text,
)
from yt_maestro.specs.schema import validate_album, validate_artist
from yt_maestro.specs.storage import load_json, set_json_fields, write_json

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
