"""Reusable interactive prompts for yt-maestro commands."""


def text(label: str, default: str | None = None) -> str:
    """Prompt for text, returning the default when the response is empty."""

    default_label = f" [{default}]" if default is not None else ""
    response = input(f"{label}{default_label}: ").strip()
    return response or default or ""


def confirm(label: str, default: bool = False) -> bool:
    """Prompt for a yes-or-no response."""

    choice = "yes" if default else "no"
    response = input(f"{label} (yes/no) [{choice}]: ").strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}
