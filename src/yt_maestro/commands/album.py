"""Commands for working with album declarations."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import library, pipelines, specs
from yt_maestro.commands import prompts
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
        help="Album filename without .json",
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
        if args.all_albums:
            return _download_all(args.library, overwrite=args.overwrite)
        return _download(
            args.album_references,
            args.library,
            overwrite=args.overwrite,
        )
    return 2


def _download(
    album_references: Sequence[str],
    library_dir: str | Path,
    *,
    overwrite: bool = False,
) -> int:
    """Load and download the selected albums from a library."""

    try:
        root = Path(library_dir).expanduser().resolve()
        config = library.load_config(root)
        albums_dir = root / config.albums_dir
        artists_dir = root / config.artists_dir
        filenames = _album_filenames(album_references)
    except (library.LibraryError, specs.SpecError) as error:
        logger.error("Cannot select albums: %s", error)
        return 1

    albums: list[tuple[str, Album]] = []
    failed = False
    for filename in filenames:
        try:
            album = specs.load_album(albums_dir / filename, artists_dir)
        except specs.SpecError as error:
            logger.error("Cannot load album %s: %s", filename.stem, error)
            failed = True
            continue
        albums.append((filename.stem, album))

    if not albums:
        if not failed:
            logger.info("No albums found")
        return 1 if failed else 0

    destination = root / config.downloads_dir
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


def _download_all(
    library_dir: str | Path,
    *,
    overwrite: bool = False,
) -> int:
    """Discover and download every album in a library."""

    try:
        root = Path(library_dir).expanduser().resolve()
        config = library.load_config(root)
        albums_dir = root / config.albums_dir
        if not albums_dir.is_dir():
            raise library.LibraryError(f"albums directory does not exist: {albums_dir}")
        references = _all_album_references(albums_dir)
    except library.LibraryError as error:
        logger.error("Cannot select albums: %s", error)
        return 1

    return _download(references, library_dir, overwrite=overwrite)


def _all_album_references(albums_dir: Path) -> list[str]:
    """Return every album reference found in a directory."""

    return [path.stem for path in sorted(albums_dir.glob("*.json"))]


def _album_filenames(album_references: Sequence[str]) -> list[Path]:
    """Normalize and deduplicate explicit album references."""

    filenames = dict.fromkeys(
        _album_filename(reference) for reference in album_references
    )
    return [Path(filename) for filename in filenames]


def _album_filename(album_reference: str) -> str:
    """Normalize an album reference to a safe JSON filename."""

    path = Path(album_reference)
    # Album references select files inside the configured directory; accepting
    # path components here would let callers escape that boundary.
    if path.name != album_reference or album_reference in {"", ".", ".."}:
        raise specs.SpecError("album reference must be a filename, not a path")
    if path.suffix and path.suffix != ".json":
        raise specs.SpecError("album reference must have no extension or use .json")
    return album_reference if path.suffix == ".json" else f"{album_reference}.json"
