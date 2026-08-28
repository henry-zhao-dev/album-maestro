import argparse
import logging
import sys
from collections.abc import Sequence

from yt_maestro.commands.album import run as run_album
from yt_maestro.commands.init import run as run_init


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="yt-maestro", description="Manage a declarative music library."
    )
    parser.add_argument("command", choices=("init", "album"))
    parsed, remaining = parser.parse_known_args(arguments)

    if parsed.command == "init":
        return run_init(remaining)
    return run_album(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
