"""Command implementations for the yt-maestro CLI."""

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from yt_maestro.commands.album import configure as configure_album
from yt_maestro.commands.album import run as run_album
from yt_maestro.commands.init import configure as configure_init
from yt_maestro.commands.init import run as run_init

CommandConfigurator = Callable[[argparse.ArgumentParser], None]
CommandRunner = Callable[[argparse.Namespace], int]


@dataclass(frozen=True)
class Command:
    """A top-level command contributed to the shared parser tree."""

    help: str
    configure: CommandConfigurator
    run: CommandRunner


COMMANDS: dict[str, Command] = {
    "init": Command(
        help="Create a new music library.",
        configure=configure_init,
        run=run_init,
    ),
    "album": Command(
        help="Work with albums in a music library.",
        configure=configure_album,
        run=run_album,
    ),
}

__all__ = ["COMMANDS", "Command"]
