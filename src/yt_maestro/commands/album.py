"""The ``album`` command group and its album-specific operations."""

import argparse
import logging
from collections.abc import Sequence

from yt_maestro import pipeline, specs
from yt_maestro.commands import prompts
from yt_maestro.commands.base import Command
from yt_maestro.library import Library, LibraryError
from yt_maestro.models import Album

logger = logging.getLogger(__name__)


class DownloadCommand(Command):
    """Implement the nested ``yt-maestro album download`` operation."""

    name = "download"
    help = "Download every track in one or more albums."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for downloading one or more albums."""

        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument(
            "album_references",
            nargs="*",
            metavar="ALBUM",
            help="Album reference in lowercase kebab-case (without .json)",
        )
        selection.add_argument(
            "--all",
            action="store_true",
            dest="all_albums",
            help="Download every album in the library",
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
            help="Overwrite existing track files without prompting",
        )

    def run(self, args: argparse.Namespace) -> int:
        """Download albums from parsed command-line arguments."""

        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        if args.all_albums:
            return self._run_download_all(music_library, overwrite=args.overwrite)
        return self._run_download(
            args.album_references,
            music_library,
            overwrite=args.overwrite,
        )

    @staticmethod
    def _run_download(
        album_references: Sequence[str],
        music_library: Library,
        *,
        overwrite: bool = False,
    ) -> int:
        """Load and download the selected albums from a library."""

        albums: list[tuple[str, Album]] = []
        failed = False
        references = dict.fromkeys(album_references)
        for reference in references:
            try:
                album = music_library.load_album(reference)
            except specs.SpecError as error:
                logger.error("Cannot load album %s: %s", reference, error)
                failed = True
                continue
            albums.append((reference.removesuffix(".json"), album))

        if not albums:
            if not failed:
                logger.info("No albums found")
            return 1 if failed else 0

        destination = music_library.downloads_dir
        existing = {
            path
            for _, album in albums
            for path in pipeline.existing_album_tracks(album, destination)
        }
        if existing:
            logger.warning("%s track files already exist", len(existing))
            for path in sorted(existing):
                logger.warning("Existing track: %s", path)

            if not overwrite and not prompts.confirm(
                "Continue and overwrite existing tracks?", default=False
            ):
                logger.info("Album download cancelled")
                return 1 if failed else 0

        for index, (reference, album) in enumerate(albums, start=1):
            logger.info("Downloading album %s of %s: %s", index, len(albums), reference)
            outputs = pipeline.download_album(album, destination)
            if len(outputs) != len(album.tracks):
                failed = True

        return 1 if failed else 0

    def _run_download_all(
        self,
        music_library: Library,
        *,
        overwrite: bool = False,
    ) -> int:
        """Discover and download every album in a library."""

        references = music_library.album_references()
        return self._run_download(references, music_library, overwrite=overwrite)


class AlbumCommand(Command):
    """Route ``yt-maestro album`` to the selected album operation."""

    name = "album"
    help = "Work with albums in a music library."

    # Album operations stay internal rather than entering the top-level registry.
    operations = {command.name: command for command in (DownloadCommand(),)}

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add the available album operations."""

        operations = parser.add_subparsers(
            dest="album_operation", metavar="COMMAND", required=True
        )
        for name, command in self.operations.items():
            operation_parser = operations.add_parser(name, help=command.help)
            command.configure(operation_parser)

    def run(self, args: argparse.Namespace) -> int:
        """Dispatch the selected album operation."""

        operation = self.operations[args.album_operation]
        return operation.run(args)
