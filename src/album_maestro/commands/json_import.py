"""The ``import`` command group and its SQLite-backed operations."""

import argparse
import logging
from pathlib import Path

from album_maestro import specs
from album_maestro.commands.base import Command
from album_maestro.library import Library, LibraryError
from album_maestro.specs import SpecError

logger = logging.getLogger(__name__)


class ImportCommand(Command):
    """The ``import`` command."""

    name = "import"
    help = "Import an album from JSON"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument(
            "--json",
            type=Path,
            metavar="FILE",
            help="An album JSON specs file",
        )
        source.add_argument(
            "--directory",
            type=Path,
            metavar="DIRECTORY",
            help="A directory containing album JSON files",
        )
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace existing albums and their tracks",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        json_paths = [args.json] if args.json else self.list_json_files(args.directory)
        if not json_paths:
            logger.error("No JSON files found")
            return 1

        failed = False

        for json_path in json_paths:
            try:
                album = specs.load_album(json_path)
                reference = music_library.create_album(
                    album, overwrite=args.overwrite
                )
            except SpecError as error:
                logger.error("Cannot import %s: %s", json_path, error)
                failed = True
            except (LibraryError, ValueError) as error:
                logger.error("Cannot import %s: %s", json_path, error)
                failed = True
            else:
                logger.info("Imported album: %s", reference)

        return 1 if failed else 0

    @classmethod
    def list_json_files(cls, directory: str | Path) -> list[Path]:
        directory = Path(directory)
        return sorted(directory.glob("*.json"))
