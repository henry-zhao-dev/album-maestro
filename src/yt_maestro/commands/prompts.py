"""Reusable interactive prompts for yt-maestro commands."""

def confirm(label: str, default: bool = False) -> bool:
    """Prompt for a yes-or-no response."""

    choice = "yes" if default else "no"
    response = input(f"{label} (yes/no) [{choice}]: ").strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}
