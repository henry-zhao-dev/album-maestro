"""Shared parsing helpers for catalog specifications."""

import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any


class SpecError(ValueError):
    """Raised when catalog configuration cannot be parsed or resolved."""


def load_json(path: str | Path, label: str) -> Any:
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


def required_string(data: Mapping[str, Any], key: str) -> str:
    """Read a required, non-empty string field."""

    value = optional_string(data, key)
    if value is None:
        raise SpecError(f"'{key}' must be a non-empty string")
    return value


def optional_string(data: Mapping[str, Any], key: str) -> str | None:
    """Read an optional string field, normalizing blanks to ``None``."""

    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise SpecError(f"'{key}' must be a string")
    return value.strip() or None


def reject_unknown_fields(
    data: Mapping[str, Any], allowed: set[str], label: str
) -> None:
    """Reject misspelled or unsupported fields rather than ignoring them."""

    unknown = sorted(set(data) - allowed)
    if unknown:
        fields = ", ".join(repr(field) for field in unknown)
        raise SpecError(f"{label} has unknown field(s): {fields}")


def artist_id(data: Mapping[str, Any], key: str = "artist") -> str:
    """Read and validate an artist catalog identifier."""

    value = required_string(data, key)
    if not all(
        part and part.isascii() and part.isalnum() and part == part.lower()
        for part in value.split("-")
    ):
        raise SpecError(f"'{key}' must be a lowercase ID such as 'beethoven'")
    return value


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
