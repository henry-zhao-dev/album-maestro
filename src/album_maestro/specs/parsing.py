"""Parse reusable values from artist and album specifications."""

import math
from collections.abc import Mapping
from typing import Any

from album_maestro.specs.errors import SpecError

__all__ = [
    "optional_string",
    "optional_timestamp",
    "required_string",
]


def required_string(
    data: Mapping[str, Any], key: str, error_type: type[ValueError] = SpecError
) -> str:
    """Read a required string, using the caller's domain-specific error."""

    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"'{key}' must be a non-empty string")
    return value.strip()


def optional_string(data: Mapping[str, Any], key: str) -> str | None:
    """Read an optional string field, normalizing blanks to ``None``."""

    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SpecError(f"'{key}' must be a string")
    return value.strip() or None


def optional_timestamp(data: Mapping[str, Any], key: str) -> int | None:
    """Read an optional timestamp field as milliseconds."""

    value = optional_string(data, key)
    return _parse_timestamp(value) if value is not None else None


def _parse_timestamp(value: str) -> int:
    """Convert ``hh:mm:ss``, ``mm:ss``, or seconds into milliseconds."""

    parts = value.split(":")
    if not 1 <= len(parts) <= 3 or any(not part for part in parts):
        raise SpecError(f"invalid timestamp: {value!r}")

    try:
        numbers = [float(part) for part in parts]
    except ValueError as error:
        raise SpecError(f"invalid timestamp: {value!r}") from error

    if any(not math.isfinite(number) or number < 0 for number in numbers):
        raise SpecError(f"invalid timestamp: {value!r}")

    while len(numbers) < 3:
        numbers.insert(0, 0.0)
    hours, minutes, seconds = numbers
    return round((hours * 3600 + minutes * 60 + seconds) * 1000)
