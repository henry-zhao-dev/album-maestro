"""Implementation of the ``yt-maestro init`` command."""

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from yt_maestro.library import Library, LibraryError

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
    args = parser.parse_args(argv)

    root = Path(args.directory).expanduser()
    default_name = root.resolve().name
    name = args.name or default_name

    try:
        music_library = Library(root=root, name=name)
        manifest = music_library.initialize()
    except LibraryError as error:
        logger.error("Cannot initialize library: %s", error)
        return 1

    print(f"Created yt-maestro library at {manifest.parent}")
    return 0
