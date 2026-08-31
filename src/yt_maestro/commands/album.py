"""The ``album`` command group and its album-specific operations."""

import argparse
import json
import logging
import re
import unicodedata
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import pipeline, specs
from yt_maestro.commands import prompts
from yt_maestro.commands.base import Command
from yt_maestro.library import Library, LibraryError
from yt_maestro.models import Album, Artist

logger = logging.getLogger(__name__)


class CreateCommand(Command):
    """Implement the nested ``yt-maestro album create`` operation."""

    name = "create"
    help = "Create a new album declaration."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for creating an album."""

        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        """Create an album declaration from interactive prompts."""

        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        title = prompts.text("Album title")
        if not title:
            logger.error("Album title must not be empty")
            return 1

        try:
            reference = _reference_from_title(title)
        except ValueError as error:
            logger.error("Cannot create album: %s", error)
            return 1

        album_path = music_library.albums_dir / f"{reference}.json"
        if album_path.exists():
            logger.error("Album already exists: %s", album_path)
            return 1

        artist_name = prompts.text("Album artist")
        try:
            artist_match = _find_artist(music_library, artist_name)
            if artist_match is None:
                artist_reference = _reference_from_text(
                    artist_name, label="artist name"
                )
                artist = None
                artist_path = music_library.artists_dir / f"{artist_reference}.json"
                if artist_path.exists():
                    raise LibraryError(
                        f"artist reference already exists: {artist_reference}"
                    )
            else:
                artist_reference, artist = artist_match
                artist_path = music_library.artists_dir / f"{artist_reference}.json"
        except (LibraryError, specs.SpecError, ValueError) as error:
            logger.error("Cannot create album: %s", error)
            return 1

        default_genre = artist.default_genre if artist is not None else None
        genre = prompts.text("Album genre (optional)", default=default_genre)

        if artist is None:
            artist_data: dict[str, object] = {"name": artist_name}
            if genre:
                artist_data["default_genre"] = genre
            try:
                _write_json(artist_path, artist_data)
            except LibraryError as error:
                logger.error("Cannot create artist: %s", error)
                return 1
        elif (
            genre
            and genre != default_genre
            and prompts.confirm(
                f"Set {genre!r} as the default genre for {artist.name}?",
                default=False,
            )
        ):
            try:
                _set_json_fields(
                    artist_path,
                    {"default_genre": genre},
                    label="artist",
                )
                default_genre = genre
            except LibraryError as error:
                logger.error("Cannot update artist: %s", error)
                return 1

        shared_url = prompts.text("Album shared URL (optional)")

        data: dict[str, object] = {
            "title": title,
            "artist": artist_reference,
        }
        if genre and artist is not None and genre != default_genre:
            data["genre"] = genre
        if shared_url:
            data["url"] = shared_url
        data["tracks"] = []

        try:
            _write_json(album_path, data)
        except LibraryError as error:
            logger.error("Cannot create album: %s", error)
            return 1

        print(f"\nAlbum created at {album_path.relative_to(music_library.root)}")
        print("You can edit JSON to create tracks.")
        return 0


class DownloadCommand(Command):
    """Implement the nested ``yt-maestro album download`` operation."""

    name = "download"
    help = "Download every track in one or more albums."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for downloading one or more albums."""

        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument(
            "album_references",
            nargs="*",
            metavar="ALBUM",
            help="Album reference in lowercase kebab-case (without .json)",
        )
        selection.add_argument(
            "--all",
            action="store_true",
            dest="all_albums",
            help="Download every album in the library",
        )
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing track files without prompting",
        )

    def run(self, args: argparse.Namespace) -> int:
        """Download albums from parsed command-line arguments."""

        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        if args.all_albums:
            return self._run_download_all(music_library, overwrite=args.overwrite)
        return self._run_download(
            args.album_references,
            music_library,
            overwrite=args.overwrite,
        )

    @staticmethod
    def _run_download(
        album_references: Sequence[str],
        music_library: Library,
        *,
        overwrite: bool = False,
    ) -> int:
        """Load and download the selected albums from a library."""

        albums: list[tuple[str, Album]] = []
        failed = False
        references = dict.fromkeys(album_references)
        for reference in references:
            try:
                album = music_library.load_album(reference)
            except specs.SpecError as error:
                logger.error("Cannot load album %s: %s", reference, error)
                failed = True
                continue
            albums.append((reference.removesuffix(".json"), album))

        if not albums:
            if not failed:
                logger.info("No albums found")
            return 1 if failed else 0

        destination = music_library.downloads_dir
        existing = {
            path
            for _, album in albums
            for path in pipeline.existing_album_tracks(album, destination)
        }
        if existing:
            logger.warning("%s track files already exist", len(existing))
            for path in sorted(existing):
                logger.warning("Existing track: %s", path)
            if not overwrite:
                overwrite = prompts.confirm("Overwrite existing tracks?", default=False)

        for index, (reference, album) in enumerate(albums, start=1):
            logger.info("Downloading album %s of %s: %s", index, len(albums), reference)
            outputs = pipeline.download_album(album, destination, overwrite)
            if len(outputs) != len(album.tracks):
                failed = True

        return 1 if failed else 0

    def _run_download_all(
        self,
        music_library: Library,
        *,
        overwrite: bool = False,
    ) -> int:
        """Discover and download every album in a library."""

        references = music_library.album_references()
        return self._run_download(references, music_library, overwrite=overwrite)


class AlbumCommand(Command):
    """Route ``yt-maestro album`` to the selected album operation."""

    name = "album"
    help = "Work with albums in a music library."

    # Album operations stay internal rather than entering the top-level registry.
    operations = {
        command.name: command for command in (CreateCommand(), DownloadCommand())
    }

    def configure(self, parser: argparse.ArgumentParser) -> None:
        """Add the available album operations."""

        operations = parser.add_subparsers(
            dest="album_operation", metavar="COMMAND", required=True
        )
        for name, command in self.operations.items():
            operation_parser = operations.add_parser(name, help=command.help)
            command.configure(operation_parser)

    def run(self, args: argparse.Namespace) -> int:
        """Dispatch the selected album operation."""

        operation = self.operations[args.album_operation]
        return operation.run(args)


def _find_artist(music_library: Library, name: str) -> tuple[str, Artist] | None:
    """Find the unique artist whose display name matches ``name``, if any."""

    if not name:
        raise LibraryError("album artist must not be empty")

    matches = [
        (reference, artist)
        for reference in music_library.artist_references()
        if (artist := music_library.load_artist(reference)).name.casefold()
        == name.casefold()
    ]
    if not matches:
        return None
    if len(matches) > 1:
        references = ", ".join(reference for reference, _ in matches)
        raise LibraryError(f"multiple artists named {name!r}: {references}")
    return matches[0]


def _reference_from_title(title: str) -> str:
    """Convert an album title to a canonical catalog reference."""

    return _reference_from_text(title, label="album title")


def _reference_from_text(value: str, *, label: str) -> str:
    """Convert display text to a canonical catalog reference."""

    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    reference = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
    if not reference:
        raise ValueError(f"{label} cannot form a catalog reference")
    return reference


def _write_json(path: Path, data: dict[str, object]) -> None:
    """Write formatted JSON without replacing an existing catalog file."""

    try:
        with path.open("x", encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")
    except FileExistsError as error:
        raise LibraryError(f"{path} already exists") from error
    except OSError as error:
        raise LibraryError(str(error)) from error


def _set_json_fields(path: Path, fields: dict[str, object], *, label: str) -> None:
    """Replace the given fields in an existing catalog file."""

    try:
        data = specs.load_json(path, label=label)
        data.update(fields)
        with path.open("w", encoding="utf-8") as output:
            json.dump(data, output, indent=2)
            output.write("\n")
    except (OSError, specs.SpecError) as error:
        raise LibraryError(str(error)) from error
