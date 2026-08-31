"""Loading and validation for persistent artist and album specifications."""

from yt_maestro.specs._parsing import SpecError
from yt_maestro.specs.catalog import load_album, load_artist

__all__ = [
    "SpecError",
    "load_album",
    "load_artist",
]
