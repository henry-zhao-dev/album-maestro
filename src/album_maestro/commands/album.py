"""The ``album`` command group and its SQLite-backed operations."""

import argparse
import logging
from collections.abc import Sequence

from album_maestro import pipeline
from album_maestro.commands import prompts
from album_maestro.commands.base import Command
from album_maestro.library import Library, LibraryError
from album_maestro.models import Album, AlbumSummary, VARIOUS_ARTISTS
from album_maestro.specs import parse_timestamp

logger = logging.getLogger(__name__)


class CreateCommand(Command):
    """Implement ``album-maestro album create``."""

    name = "create"
    help = "Create a new album."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        title = prompts.text("Album title")
        artist = prompts.text("Album artist (optional)")
        composer = prompts.text("Album composer (optional)")
        genre = prompts.text("Album genre")
        shared_url = prompts.text("Album shared URL (optional)")

        try:
            reference = music_library.create_album(
                Album(
                    title=title,
                    artist=artist or None,
                    composer=composer or None,
                    genre=genre,
                    url=shared_url or None,
                    tracks=(),
                )
            )
        except (LibraryError, ValueError) as error:
            logger.error("Cannot create album: %s", error)
            return 1

        print(f"\nAlbum created: {reference}")
        print("The album has no tracks yet. Use 'album edit' to add tracks.")
        return 0


class ListCommand(Command):
    """Implement ``album-maestro album list``."""

    name = "list"
    help = "List albums in a music library."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
            albums = music_library.list_albums()
        except LibraryError as error:
            logger.error("Cannot list albums: %s", error)
            return 1
        _print_album_table(albums)
        return 0


class SearchCommand(Command):
    """Implement ``album-maestro album search``."""

    name = "search"
    help = "Search album metadata."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--title", help="Match album titles")
        parser.add_argument("--artist", help="Match album artists")
        parser.add_argument("--composer", help="Match composers")
        parser.add_argument("--genre", help="Match genres")
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
            albums = music_library.search_albums(
                title=args.title,
                artist=args.artist,
                composer=args.composer,
                genre=args.genre,
            )
        except LibraryError as error:
            logger.error("Cannot search albums: %s", error)
            return 1
        _print_album_table(albums)
        return 0


class ShowCommand(Command):
    """Implement ``album-maestro album show``."""

    name = "show"
    help = "Show an album and its tracks."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            album = Library.load(args.library).load_album(args.reference)
        except LibraryError as error:
            logger.error("Cannot show album: %s", error)
            return 1

        print(f"Title:        {album.title}")
        print(f"Artist:       {album.artist or VARIOUS_ARTISTS}")
        print(f"Album artist: {album.resolved_album_artist()}")
        print(f"Composer:     {album.composer or '—'}")
        print(f"Genre:        {album.genre}")
        print(f"Source:       {album.url or '—'}")
        print()
        print("TRACKS")
        if not album.tracks:
            print("  No tracks yet.")
            return 0

        print("  #  TITLE                                      START    END")
        for position, track in enumerate(album.tracks, start=1):
            print(
                f"{position:>3}  {track.title:<42} "
                f"{_format_timestamp(track.start_ms):<8} "
                f"{_format_timestamp(track.end_ms)}"
            )
        return 0


class EditCommand(Command):
    """Implement interactive album and track editing."""

    name = "edit"
    help = "Edit an album and its tracks."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
            album = music_library.load_album(args.reference)
            music_library.update_album(
                args.reference,
                title=prompts.text("Album title", album.title),
                artist=prompts.text("Album artist (optional)", album.artist),
                composer=prompts.text("Album composer (optional)", album.composer),
                genre=prompts.text("Album genre", album.genre),
                url=prompts.text("Album shared URL (optional)", album.url),
            )
        except (LibraryError, ValueError) as error:
            logger.error("Cannot edit album: %s", error)
            return 1

        while True:
            print("\nTrack actions: [a]dd, [e]dit, [r]emove, [d]one")
            action = prompts.text("Choose an action").casefold()
            if action in {"d", "done"}:
                return 0
            try:
                if action in {"a", "add"}:
                    _add_track(music_library, args.reference)
                elif action in {"e", "edit"}:
                    _edit_track(music_library, args.reference)
                elif action in {"r", "remove"}:
                    _remove_track(music_library, args.reference)
                else:
                    print("Please choose add, edit, remove, or done.")
            except (LibraryError, ValueError) as error:
                logger.error("Cannot edit track: %s", error)
                return 1


class DeleteCommand(Command):
    """Implement ``album-maestro album delete`` command."""

    name = "delete"
    help = "Delete an album."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")
        parser.add_argument(
            "--library",
            default=".",
            metavar="DIRECTORY",
            help="Library directory (default: current directory)",
        )

    def run(self, args: argparse.Namespace) -> int:
        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1

        reference = args.reference
        try:
            music_library.delete_album(reference)
            logger.info("Deleted album: %s", reference)
        except (LibraryError, ValueError) as error:
            logger.error("Cannot delete album: %s", error)
            return 1

        return 0


class DownloadCommand(Command):
    """Implement ``album-maestro album download``."""

    name = "download"
    help = "Download every track in one or more albums."

    def configure(self, parser: argparse.ArgumentParser) -> None:
        selection = parser.add_mutually_exclusive_group(required=True)
        selection.add_argument(
            "album_references",
            nargs="*",
            metavar="ALBUM",
            help="Album reference in lowercase kebab-case",
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
        try:
            music_library = Library.load(args.library)
        except LibraryError as error:
            logger.error("Cannot load library: %s", error)
            return 1
        references = (
            music_library.album_references()
            if args.all_albums
            else args.album_references
        )
        return self._run_download(references, music_library, overwrite=args.overwrite)

    @staticmethod
    def _run_download(
        album_references: Sequence[str],
        music_library: Library,
        *,
        overwrite: bool = False,
    ) -> int:
        albums: list[tuple[str, Album]] = []
        failed = False
        for reference in dict.fromkeys(album_references):
            try:
                album = music_library.load_album(reference)
            except LibraryError as error:
                logger.error("Cannot load album %s: %s", reference, error)
                failed = True
                continue
            if not album.tracks:
                logger.error("Album %s has no tracks", reference)
                failed = True
                continue
            albums.append((reference, album))

        if not albums:
            if not failed:
                logger.info("No albums found")
            return 1 if failed else 0

        destination = music_library.downloads_dir
        try:
            existing = {
                path
                for _, album in albums
                for path in pipeline.existing_album_tracks(album, destination)
            }
        except ValueError as error:
            logger.error("Cannot resolve album tracks: %s", error)
            return 1
        if existing:
            logger.warning("%s track files already exist", len(existing))
            for path in sorted(existing):
                logger.warning("Existing track: %s", path)
            if not overwrite:
                overwrite = prompts.confirm("Overwrite existing tracks?", default=False)

        for index, (reference, album) in enumerate(albums, start=1):
            logger.info("Downloading album %s of %s: %s", index, len(albums), reference)
            try:
                outputs = pipeline.download_album(album, destination, overwrite)
            except ValueError as error:
                logger.error("Cannot download album %s: %s", reference, error)
                failed = True
                continue
            if len(outputs) != len(album.tracks):
                failed = True
        return 1 if failed else 0


class AlbumCommand(Command):
    """Route ``album-maestro album`` to its operations."""

    name = "album"
    help = "Work with albums in a music library."

    operations = {
        command.name: command
        for command in (
            CreateCommand(),
            ListCommand(),
            SearchCommand(),
            ShowCommand(),
            EditCommand(),
            DeleteCommand(),
            DownloadCommand(),
        )
    }

    def configure(self, parser: argparse.ArgumentParser) -> None:
        operations = parser.add_subparsers(
            dest="album_operation", metavar="COMMAND", required=True
        )
        for name, command in self.operations.items():
            operation_parser = operations.add_parser(name, help=command.help)
            command.configure(operation_parser)

    def run(self, args: argparse.Namespace) -> int:
        return self.operations[args.album_operation].run(args)


def _print_album_table(albums: Sequence[AlbumSummary]) -> None:
    """Print album summaries in a compact, aligned table."""

    if not albums:
        print("No albums found.")
        return
    headers = ("REFERENCE", "TITLE", "ARTIST", "GENRE", "TRACKS")
    rows = [
        (
            album.reference,
            album.title,
            album.artist or VARIOUS_ARTISTS,
            album.genre,
            str(album.track_count),
        )
        for album in albums
    ]
    widths = [
        max(len(header), *(len(row[index]) for row in rows))
        for index, header in enumerate(headers)
    ]
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


def _add_track(music_library: Library, reference: str) -> None:
    """Prompt for and append one track."""

    album = music_library.load_album(reference)
    title = prompts.text("Track title")
    artist = prompts.override_text("Track artist (optional)", album.artist)
    composer = prompts.override_text("Track composer (optional)", album.composer)
    genre = prompts.override_text("Track genre (optional)", album.genre)
    url = prompts.override_text("Track URL (optional)", album.url)
    start_ms = _prompt_timestamp("Track start (optional)")
    end_ms = _prompt_timestamp("Track end (optional)")
    position = music_library.create_track(
        reference,
        title=title,
        artist=artist,
        composer=composer,
        genre=genre,
        url=url,
        start_ms=start_ms,
        end_ms=end_ms,
    )
    print(f"Added track {position}.")


def _edit_track(music_library: Library, reference: str) -> None:
    """Prompt for and update one existing track."""

    album = music_library.load_album(reference)
    if not album.tracks:
        print("No tracks found.")
        return
    position = prompts.bounded_number("Track number", 1, len(album.tracks))
    track = album.tracks[position - 1]
    music_library.update_track(
        reference,
        position,
        title=prompts.text("Track title", track.title),
        artist=prompts.override_text(
            "Track artist (optional)", track.artist or album.artist
        ),
        composer=prompts.override_text(
            "Track composer (optional)", track.composer or album.composer
        ),
        genre=prompts.override_text(
            "Track genre (optional)", track.genre or album.genre
        ),
        url=prompts.override_text("Track URL (optional)", track.url or album.url),
        start_ms=_prompt_timestamp("Track start (optional)", track.start_ms),
        end_ms=_prompt_timestamp("Track end (optional)", track.end_ms),
    )
    print(f"Updated track {position}.")


def _remove_track(music_library: Library, reference: str) -> None:
    """Prompt for and delete one existing track."""

    album = music_library.load_album(reference)
    if not album.tracks:
        print("No tracks found.")
        return
    position = prompts.bounded_number("Track number", 1, len(album.tracks))
    if prompts.confirm(f"Remove track {position}?", default=False):
        music_library.delete_track(reference, position)
        print(f"Removed track {position}.")


def _prompt_timestamp(label: str, default_ms: int | None = None) -> int | None:
    """Prompt for a timestamp, retrying malformed values."""

    default = _format_timestamp(default_ms) if default_ms is not None else None
    while True:
        value = prompts.text(label, default)
        if not value:
            return None
        try:
            return parse_timestamp(value)
        except ValueError:
            print("Please enter a timestamp such as 1:23 or 1:02:03.")


def _format_timestamp(value_ms: int | None) -> str:
    """Format milliseconds for human-readable CLI output."""

    if value_ms is None:
        return "—"
    total_seconds, milliseconds = divmod(value_ms, 1000)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    if milliseconds:
        return f"{minutes}:{seconds:02}.{milliseconds:03}"
    return f"{minutes}:{seconds:02}"
