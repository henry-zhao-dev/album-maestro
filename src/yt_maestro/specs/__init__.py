"""Loading and validation for persistent artist and album specifications."""

from yt_maestro.specs._parsing import SpecError, parse_timestamp
from yt_maestro.specs.album import load_album, parse_album
from yt_maestro.specs.artist import load_artist, parse_artist

__all__ = [
    "SpecError",
    "load_album",
    "load_artist",
    "parse_album",
    "parse_artist",
    "parse_timestamp",
]
