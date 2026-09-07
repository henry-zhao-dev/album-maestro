"""Read and write JSON specification documents."""

import json
from pathlib import Path
from typing import Any

from album_maestro.specs.errors import SpecError


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


def write_json(
    path: Path, data: dict[str, object], *, overwrite: bool = False
) -> None:
    """Write formatted JSON, optionally replacing an existing file."""

    try:
        mode = "w" if overwrite else "x"
        with path.open(mode, encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")
    except FileExistsError as error:
        raise SpecError(f"{path} already exists") from error
    except OSError as error:
        raise SpecError(str(error)) from error


def set_json_fields(path: Path, fields: dict[str, object], *, label: str) -> None:
    """Replace the given fields in an existing JSON object."""

    data = load_json(path, label=label)
    if not isinstance(data, dict):
        raise SpecError(f"{label} must contain a JSON object")
    data.update(fields)

    try:
        with path.open("w", encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")
    except OSError as error:
        raise SpecError(str(error)) from error
