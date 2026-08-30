"""Registry of commands available directly beneath ``yt-maestro``."""

from yt_maestro.commands.album import AlbumCommand
from yt_maestro.commands.base import Command
from yt_maestro.commands.init import InitCommand

_registered_commands = (
    InitCommand(),
    AlbumCommand(),
)

# Nested operations such as ``album download`` are owned by their parent command.
COMMANDS: dict[str, Command] = {
    command.name: command for command in _registered_commands
}

__all__ = ["COMMANDS", "Command"]
