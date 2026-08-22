import argparse
import logging

from yt_maestro import pipeline, spec


def main() -> int:
    logging.basicConfig(level=logging.INFO)

    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Download media from YouTube using spec JSON files."
    )
    parser.add_argument(
        "spec_files",
        nargs="+",  # Accepts 1 or more file paths
        help="Path(s) to spec JSON file(s)",
    )
    args = parser.parse_args()

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
