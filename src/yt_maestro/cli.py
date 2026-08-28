"""Top-level command-line entry point."""

import argparse
import logging
import sys
from collections.abc import Sequence

from yt_maestro.commands import COMMANDS


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch command-line arguments to the selected command group."""

    logging.basicConfig(level=logging.INFO)
    arguments = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(
        prog="yt-maestro", description="Manage a declarative music library."
    )
    parser.add_argument("command", choices=COMMANDS)
    parsed, remaining = parser.parse_known_args(arguments)

    run_command = COMMANDS[parsed.command]
    return run_command(remaining)


if __name__ == "__main__":
    raise SystemExit(main())
