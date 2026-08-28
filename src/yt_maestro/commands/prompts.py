"""Reusable interactive prompts for yt-maestro commands."""

from pathlib import Path

from yt_maestro import library


def prompt(label: str, default: str) -> str:
    """Prompt for a string, returning the default for an empty response."""

    response = input(f"{label} [{default}]: ").strip()
    return response or default


def prompt_path(label: str, default: Path) -> Path:
    """Prompt until a valid relative library directory path is provided."""

    while True:
        response = input(f"{label} [{default}]: ").strip()
        path = Path(response) if response else default
        try:
            library.validate_directory_path(label.lower(), path)
        except library.LibraryError as error:
            print(f"Invalid path: {error}")
            continue
        break

    return path


def confirm(label: str, default: bool = False) -> bool:
    """Prompt for a yes-or-no response."""

    choice = "yes" if default else "no"
    response = input(f"{label} (yes/no) [{choice}]: ").strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}
