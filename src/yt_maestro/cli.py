"""Top-level command-line entry point."""

import argparse
import logging
import sys
from collections.abc import Sequence

from yt_maestro.commands import COMMANDS

LOG_FORMAT = "[%(levelname)s] %(message)s"


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch command-line arguments to the selected command group."""

    logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="yt-maestro", description="Manage a declarative music library."
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND", required=True)
    for name, command in COMMANDS.items():
        command_parser = commands.add_parser(name, help=command.help)
        command.configure(command_parser)

    if not arguments:
        parser.print_help()
        return 0

    parsed = parser.parse_args(arguments)

    command = COMMANDS[parsed.command]
    return command.run(parsed)


if __name__ == "__main__":
    raise SystemExit(main())
