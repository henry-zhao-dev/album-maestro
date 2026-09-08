"""The ``import`` and ``export`` commands and their SQLite-backed operations."""

import argparse
import logging
from pathlib import Path

from album_maestro import specs
from album_maestro.commands.base import LibraryCommand
from album_maestro.library import Library, LibraryError
from album_maestro.specs import SpecError

logger = logging.getLogger(__name__)


class ImportCommand(LibraryCommand):
    """The ``import`` command."""

    name = "import"
    help = "Import an album from JSON"

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
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
            "--overwrite",
            action="store_true",
            help="Replace existing albums and their tracks",
        )

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        json_paths = [args.json] if args.json else self.list_json_files(args.directory)
        if not json_paths:
            logger.error("No JSON files found")
            return 1

        failed = False

        for json_path in json_paths:
            try:
                album = specs.load_album(json_path)
                reference = library.create_album(album, overwrite=args.overwrite)
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


class ExportCommand(LibraryCommand):
    """Export SQLite album data as JSON specifications."""

    name = "export"
    help = "Export albums to JSON specifications."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument(
            "album_references",
            nargs="*",
            metavar="ALBUM",
            help="Album reference(s) to export",
        )
        selection.add_argument(
            "--all",
            action="store_true",
            dest="all_albums",
            help="Export every album in the library",
        )
        destination = parser.add_mutually_exclusive_group(required=True)
        destination.add_argument(
            "--json",
            type=Path,
            metavar="FILE",
            help="JSON output file; requires exactly one album",
        )
        destination.add_argument(
            "--directory",
            type=Path,
            metavar="DIRECTORY",
            help="Directory for one JSON file per album",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Replace existing JSON output files",
        )

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        references = (
            library.album_references() if args.all_albums else args.album_references
        )

        if args.json:
            if len(references) != 1:
                logger.error("--json requires exactly one album reference")
                return 1
            return self._export_one(library, references[0], args.json, args.overwrite)

        assert args.directory is not None
        args.directory.mkdir(parents=True, exist_ok=True)
        failed = False
        for reference in dict.fromkeys(references):
            output = args.directory / f"{reference}.json"
            if self._export_one(library, reference, output, args.overwrite):
                failed = True
        return 1 if failed else 0

    @staticmethod
    def _export_one(
        music_library: Library,
        reference: str,
        output: Path,
        overwrite: bool,
    ) -> int:
        try:
            album = music_library.load_album(reference)
            output.parent.mkdir(parents=True, exist_ok=True)
            specs.write_json(output, specs.dump_album(album), overwrite=overwrite)
        except (LibraryError, SpecError) as error:
            logger.error("Cannot export %s: %s", reference, error)
            return 1
        logger.info("Exported album %s to %s", reference, output)
        return 0
