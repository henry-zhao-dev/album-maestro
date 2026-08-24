import argparse
import logging
import sys
from collections.abc import Sequence

from yt_maestro import pipeline, spec
from yt_maestro.commands.init import run as run_init


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO)
    arguments = list(argv) if argv is not None else sys.argv[1:]

    if arguments and arguments[0] == "init":
        return run_init(arguments[1:])

    return _run_legacy_specs(arguments)


def _run_legacy_specs(argv: Sequence[str]) -> int:
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Download media from YouTube using spec JSON files.",
        epilog="Create a declarative music library with: yt-maestro init",
    )
    parser.add_argument(
        "spec_files",
        nargs="+",  # Accepts 1 or more file paths
        help="Path(s) to spec JSON file(s)",
    )
    args = parser.parse_args(argv)

    exit_code = 0
    for spec_path in args.spec_files:
        try:
            tracks = spec.load_specs(spec_path)
        except spec.SpecError as error:
            logging.error("Cannot load %s: %s", spec_path, error)
            exit_code = 1
            continue

        logging.info("Loaded %s", spec_path)
        outputs = pipeline.process_specs(tracks)
        if len(outputs) != len(tracks):
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
