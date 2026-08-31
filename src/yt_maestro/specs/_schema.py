"""Load and apply the JSON Schemas shipped with yt-maestro."""

import json
from collections.abc import Mapping
from functools import cache
from importlib.resources import files
from typing import Any, cast

from jsonschema import Draft202012Validator

from yt_maestro.specs._parsing import SpecError


def validate_object(data: Any, schema_name: str, *, label: str) -> Mapping[str, Any]:
    """Validate a decoded catalog object and return it with a narrowed type."""

    error = min(
        _validator(schema_name).iter_errors(data),
        key=lambda err: tuple(map(str, err.absolute_path)),
        default=None,
    )
    if error is not None:
        location = _format_location(label, error.absolute_path)
        raise SpecError(f"{location}: {error.message}")
    return cast(Mapping[str, Any], data)


@cache
def _validator(schema_name: str) -> Draft202012Validator:
    """Load and compile a packaged schema once per process."""

    resource = files("yt_maestro").joinpath("schemas", f"{schema_name}.schema.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _format_location(label: str, path: Any) -> str:
    """Render a JSON Schema error path in familiar dotted notation.

    Example:
        >>> _format_location("catalog", ["channels", 0, "name"])
        'catalog.channels[0].name'
    """

    return label + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in path
    )
