"""Registry of commands available directly beneath ``album-maestro``."""

from album_maestro.commands import album, sync
from album_maestro.commands.base import Command
from album_maestro.commands.initialize import InitCommand

_registered_commands = (
    InitCommand(),
    album.CreateCommand(),
    album.ListCommand(),
    album.SearchCommand(),
    album.ShowCommand(),
    album.EditCommand(),
    album.DeleteCommand(),
    album.DownloadCommand(),
    sync.ImportCommand(),
    sync.ExportCommand(),
)

# Album operations are registered directly beneath the root parser.
COMMANDS: dict[str, Command] = {
    command.name: command for command in _registered_commands
}

__all__ = ["COMMANDS", "Command"]
