import argparse
import json
import logging

from yt_maestro import yt_spec


def main():
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

    # Process each spec file passed via CLI
    for spec_path in args.spec_files:
        try:
            with open(spec_path, encoding="utf-8") as spec_file:
                specs = json.load(spec_file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            logging.exception(f"Cannot load {spec_path}")
            continue

        logging.info(f"Loaded {spec_path}")
        yt_spec.download_from_spec(specs)


if __name__ == "__main__":
    main()
