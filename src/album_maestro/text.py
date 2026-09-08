"""Shared text normalization helpers."""


def normalize_text(value: str) -> str:
    """Strip surrounding whitespace from one text value."""

    return value.strip()


def optional_text(value: str | None) -> str | None:
    """Normalize optional text to ``None`` when blank."""

    normalized = normalize_text(value) if value is not None else ""
    return normalized or None


def required_text(
    value: str | None,
    *,
    label: str,
    error_type: type[ValueError] = ValueError,
) -> str:
    """Normalize required text or raise the requested validation error."""

    normalized = optional_text(value)
    if normalized is None:
        raise error_type(f"{label} must not be empty")
    return normalized
