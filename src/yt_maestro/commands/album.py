"""Commands for working with album declarations."""

import argparse
import logging
from collections.abc import Sequence

from yt_maestro import pipelines, specs
from yt_maestro.commands import prompts
from yt_maestro.library import Library, LibraryError
from yt_maestro.models import Album

logger = logging.getLogger(__name__)


def run(argv: Sequence[str]) -> int:
    """Run an ``yt-maestro album`` subcommand."""

    parser = argparse.ArgumentParser(
        prog="yt-maestro album", description="Work with albums in a music library."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser(
        "download", help="Download every track in one or more albums."
    )
    download.add_argument(
        "album_references",
        nargs="*",
        metavar="ALBUM",
        help="Album reference in lowercase kebab-case (without .json)",
    )
    download.add_argument(
        "--all",
        action="store_true",
        dest="all_albums",
        help="Download every album in the library",
    )
    download.add_argument(
        "--library",
        default=".",
        metavar="DIRECTORY",
        help="Library directory (default: current directory)",
    )
    download.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing track files without prompting",
    )
    args = parser.parse_args(list(argv))

    if args.command == "download":
        if args.all_albums and args.album_references:
            download.error("album references cannot be combined with --all")
        if not args.all_albums and not args.album_references:
            download.error("provide at least one album reference or use --all")

        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        if args.all_albums:
            return _run_download_all(music_library, overwrite=args.overwrite)
        return _run_download(
            args.album_references,
            music_library,
            overwrite=args.overwrite,
        )

    return 2


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
        for path in pipelines.existing_album_tracks(album, destination)
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
        logger.info(
            "Downloading album %s of %s: %s", index, len(albums), reference
        )
        outputs = pipelines.download_album(album, destination)
        if len(outputs) != len(album.tracks):
            failed = True

    return 1 if failed else 0


def _run_download_all(
    music_library: Library,
    *,
    overwrite: bool = False,
) -> int:
    """Discover and download every album in a library."""

    references = music_library.album_references()
    return _run_download(references, music_library, overwrite=overwrite)
