"""Implementation of the ``yt-maestro init`` command."""

import argparse
import json
import logging
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import library
from yt_maestro.commands import prompts

logger = logging.getLogger(__name__)


def run(argv: Sequence[str]) -> int:
    """Initialize a yt-maestro library from command-line arguments."""

    parser = argparse.ArgumentParser(
        prog="yt-maestro init",
        description=(
            "Create a yt-maestro library for downloading and organizing music "
            "from YouTube."
        ),
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=".",
        help="Library directory (default: current directory)",
    )
    parser.add_argument("--name", help="Library name")
    parser.add_argument(
        "--albums-dir",
        type=Path,
        default=library.DEFAULT_ALBUMS_DIR,
    )
    parser.add_argument(
        "--artists-dir",
        type=Path,
        default=library.DEFAULT_ARTISTS_DIR,
    )
    parser.add_argument(
        "--downloads-dir",
        type=Path,
        default=library.DEFAULT_DOWNLOADS_DIR,
    )
    parser.add_argument(
        "-n",
        "--no-interaction",
        action="store_true",
        help="Use defaults and command-line options without prompting",
    )
    args = parser.parse_args(argv)

    root = Path(args.directory).expanduser()
    default_name = root.resolve().name
    name = args.name or default_name
    albums_dir = args.albums_dir
    artists_dir = args.artists_dir
    downloads_dir = args.downloads_dir

    if not args.no_interaction:
        name = prompts.prompt("Library name", name)
        albums_dir = prompts.prompt_path("Albums directory", albums_dir)
        artists_dir = prompts.prompt_path("Artists directory", artists_dir)
        downloads_dir = prompts.prompt_path("Downloads directory", downloads_dir)

    config = library.LibraryConfig(
        name=name,
        albums_dir=albums_dir,
        artists_dir=artists_dir,
        downloads_dir=downloads_dir,
    )

    if not args.no_interaction:
        print("\nGenerated configuration:\n")
        print(json.dumps(config.as_dict(), indent=2))
        if not prompts.confirm("Do you confirm generation?", default=True):
            print("Initialization cancelled.")
            return 0

    try:
        manifest = library.initialize(root, config)
    except library.LibraryError as error:
        logger.error("Cannot initialize library: %s", error)
        return 1

    print(f"Created yt-maestro library at {manifest.parent}")
    return 0
