"""Build the root parser and dispatch to a registered top-level command."""

import argparse
import logging
import sys
from collections.abc import Sequence

from album_maestro.commands import COMMANDS

LOG_FORMAT = "[%(levelname)s] %(message)s"


def main(argv: Sequence[str] | None = None) -> int:
    """Configure the CLI, parse arguments once, and run the selected command."""

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="album-maestro",
        description="Turn recordings into albums you can keep and play.",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)

    # Each command owns the arguments beneath its top-level parser.
    for name, command in COMMANDS.items():
        command_parser = commands.add_parser(name, help=command.help)
        command.configure(command_parser)

    if not arguments:
        parser.print_help()
        return 0

    parsed = parser.parse_args(arguments)

    # argparse stores the selected subparser name in ``parsed.command``.
    command = COMMANDS[parsed.command]
    return command.run(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
