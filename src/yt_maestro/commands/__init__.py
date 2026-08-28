"""Command implementations for the yt-maestro CLI."""

from collections.abc import Callable, Sequence

from yt_maestro.commands.album import run as run_album
from yt_maestro.commands.init import run as run_init

Command = Callable[[Sequence[str]], int]

COMMANDS: dict[str, Command] = {
    "init": run_init,
    "album": run_album,
}

__all__ = ["COMMANDS", "Command"]
