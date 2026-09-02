"""Implementation of the ``album-maestro init`` command."""

import argparse
import logging
from pathlib import Path

from album_maestro.commands.base import Command
from album_maestro.library import Library, LibraryError

logger = logging.getLogger(__name__)


class InitCommand(Command):
    """Create a declarative music library."""

    name = "init"
    help = "Create a new music library."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for initializing a music library."""

        parser.add_argument(
            "directory",
            nargs="?",
            default=".",
            help="Library directory (default: current directory)",
        )
        parser.add_argument("--name", help="Library name")

    def run(self, args: argparse.Namespace) -> int:
        """Initialize a music library from parsed command-line arguments."""

        root = Path(args.directory).expanduser()
        default_name = root.resolve().name
        name = args.name or default_name

        try:
            music_library = Library(root=root, name=name)
            manifest = music_library.initialize()
        except LibraryError as error:
            logger.error("Cannot initialize library: %s", error)
            return 1

        print(f"Created Album Maestro library at {manifest.parent}")
        return 0
