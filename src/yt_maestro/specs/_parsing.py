"""Shared parsing helpers for catalog specifications."""

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """Raised when catalog configuration cannot be parsed or resolved."""


def load_json(path: str | Path, *, label: str) -> Any:
    """Read a JSON file and report errors using catalog terminology."""

    try:
        with Path(path).open(encoding="utf-8") as json_file:
            return json.load(json_file)
    except OSError as error:
        raise SpecError(f"cannot read {label}: {error}") from error
    except json.JSONDecodeError as error:
        raise SpecError(
            f"invalid {label} JSON at line {error.lineno}: {error.msg}"
        ) from error


def optional_string(data: Mapping[str, Any], key: str) -> str | None:
    """Read an optional string field, normalizing blanks to ``None``."""

    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SpecError(f"'{key}' must be a string")
    return value.strip() or None


def required_string(
    data: Mapping[str, Any], key: str, error_type: type[ValueError] = SpecError
) -> str:
    """Read a required string, using the caller's domain-specific error."""

    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise error_type(f"'{key}' must be a non-empty string")
    return value.strip()


def catalog_reference(value: str, *, label: str) -> str:
    """Validate a lowercase kebab-case catalog reference."""

    if not all(
        part and part.isascii() and part.isalnum() and part == part.lower()
        for part in value.split("-")
    ):
        raise SpecError(
            f"{label} reference must be lowercase kebab-case, such as 'beethoven'"
        )
    return value


def artist_reference(data: Mapping[str, Any], key: str = "artist") -> str:
    """Read and validate an artist reference from catalog data."""

    return catalog_reference(required_string(data, key), label=key)


def optional_timestamp(data: Mapping[str, Any], key: str) -> int | None:
    """Read an optional timestamp field as milliseconds."""

    value = optional_string(data, key)
    return parse_timestamp(value) if value is not None else None


def parse_timestamp(value: str) -> int:
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
