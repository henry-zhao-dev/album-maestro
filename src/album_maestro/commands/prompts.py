"""Reusable interactive prompts for album-maestro commands."""


def text(label: str, default: str | None = None) -> str:
    """Prompt for text, returning the default when the response is empty."""

    default_label = f" [{default}]" if default is not None else ""
    response = input(f"{label}{default_label}: ").strip()
    return response or default or ""


def override_text(label: str, default: str | None = None) -> str:
    """Prompt for an optional override, preserving blank as no override."""

    default_label = f" [{default}]" if default is not None else ""
    return input(f"{label}{default_label}: ").strip()


def number(label: str, default: int | None = None) -> int:
    """Prompt for an integer, requiring one when no default is provided."""

    default_label = f" [{default}]" if default is not None else ""
    value: int | None = None

    while value is None:
        response = input(f"{label}{default_label}: ").strip()
        if not response:
            value = default
            continue

        try:
            value = int(response)
        except ValueError:
            print("Please enter a whole number.")

    return value


def bounded_number(
    label: str,
    minimum: int,
    maximum: int,
    default: int | None = None,
) -> int:
    """Prompt for an integer within inclusive bounds."""

    if minimum > maximum:
        raise ValueError("minimum must not be greater than maximum")
    if default is not None and not minimum <= default <= maximum:
        raise ValueError("default must be within the allowed range")

    while True:
        value = number(label, default)
        if minimum <= value <= maximum:
            return value
        print(f"Please enter a number from {minimum} to {maximum}.")


def confirm(label: str, default: bool = False) -> bool:
    """Prompt for a yes-or-no response."""

    choice = "yes" if default else "no"
    response = input(f"{label} (yes/no) [{choice}]: ").strip().lower()
    if not response:
        return default
    return response in {"y", "yes"}
