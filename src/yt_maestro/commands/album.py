"""Commands for working with album declarations."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import library, specs
from yt_maestro.pipelines import album as album_pipeline


def run(argv: Sequence[str]) -> int:
    """Run an ``yt-maestro album`` subcommand."""

    parser = argparse.ArgumentParser(
        prog="yt-maestro album", description="Work with albums in a music library."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser(
        "download", help="Download and process every track in an album."
    )
    download.add_argument("album_name", help="Album filename without .json")
    download.add_argument(
        "--library",
        default=".",
        metavar="DIRECTORY",
        help="Library directory (default: current directory)",
    )
    args = parser.parse_args(list(argv))

    if args.command == "download":
        return _download(args.album_name, args.library)
    return 2


def _download(album_name: str, library_dir: str | Path) -> int:
    try:
        filename = _album_filename(album_name)
        root = Path(library_dir).expanduser().resolve()
        config = library.load_config(root)
        album = specs.load_album(
            root / config.albums_dir / filename,
            root / config.artists_dir,
        )
        outputs = album_pipeline.process_album(album, root / config.downloads_dir)
    except (library.LibraryError, specs.SpecError) as error:
        logging.error("Cannot download album %s: %s", album_name, error)
        return 1

    expected = len(album.tracks)
    logging.info("Created %s of %s album tracks", len(outputs), expected)
    return 0 if len(outputs) == expected else 1


def _album_filename(album_name: str) -> str:
    path = Path(album_name)
    if path.name != album_name or album_name in {"", ".", ".."}:
        raise specs.SpecError("album name must be a filename, not a path")
    if path.suffix and path.suffix != ".json":
        raise specs.SpecError("album name must have no extension or use .json")
    return album_name if path.suffix == ".json" else f"{album_name}.json"
