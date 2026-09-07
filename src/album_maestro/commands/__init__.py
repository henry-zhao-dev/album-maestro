"""Registry of commands available directly beneath ``album-maestro``."""

from album_maestro.commands.album import AlbumCommand
from album_maestro.commands.base import Command
from album_maestro.commands.initialize import InitCommand
from album_maestro.commands.json_import import ImportCommand

_registered_commands = (
    InitCommand(),
    AlbumCommand(),
    ImportCommand(),
)

# Nested operations such as ``album download`` are owned by their parent command.
COMMANDS: dict[str, Command] = {
    command.name: command for command in _registered_commands
}

__all__ = ["COMMANDS", "Command"]
