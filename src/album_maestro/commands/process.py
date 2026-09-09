"""Process local source audio into library track files."""

import argparse
import logging
import tempfile
from pathlib import Path

from album_maestro import pipeline
from album_maestro.commands.base import LibraryCommand
from album_maestro.library import Library, LibraryError

logger = logging.getLogger(__name__)


class ProcessCommand(LibraryCommand):
    """Implement ``album-maestro process``."""

    name = "process"
    help = "Process local source audio into tracks."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument(
            "album_references",
            nargs="*",
            metavar="ALBUM",
            help="Album reference(s) to process",
        )
        selection.add_argument(
            "--all",
            action="store_true",
            dest="all_albums",
            help="Process every album in the library",
        )
        parser.add_argument(
            "--output",
            type=Path,
            default=Path("tracks"),
            metavar="DIRECTORY",
            help="Processed track directory (default: tracks)",
        )

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        references = (
            library.album_references() if args.all_albums else args.album_references
        )
        if not references:
            logger.error("Provide at least one album reference or use --all")
            return 1

        destination = Path(args.output)
        if not destination.is_absolute():
            destination = library.root / destination
        destination.mkdir(parents=True, exist_ok=True)

        failed = False
        with tempfile.TemporaryDirectory(prefix=".album-maestro-process-") as work:
            work_dir = Path(work)
            for reference in dict.fromkeys(references):
                if self._process_album(library, reference, destination, work_dir):
                    failed = True
        return 1 if failed else 0

    @staticmethod
    def _process_album(
        library: Library,
        reference: str,
        destination: Path,
        work_dir: Path,
    ) -> bool:
        """Process every track in one album, continuing after track failures."""

        try:
            album = library.load_album(reference)
            requests = album.requests()
        except (LibraryError, ValueError) as error:
            logger.error("Cannot process %s: %s", reference, error)
            return True

        if not requests:
            logger.info("Skipping %s: album has no tracks", reference)
            return False

        failed = False
        for position, track in enumerate(requests, start=1):
            try:
                if track.file_source is None:
                    raise LibraryError("track has no local file source")
                source = library.resolve_file_source(track.file_source)
                output = pipeline.create_track(
                    track,
                    source,
                    destination,
                    work_dir,
                )
            except Exception as error:  # continue with the remaining tracks
                logger.error(
                    "Cannot process %s track %d: %s", reference, position, error
                )
                failed = True
            else:
                logger.info("Processed %s track %d: %s", reference, position, output)
        return failed
