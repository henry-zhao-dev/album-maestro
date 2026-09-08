"""Top-level album commands and their SQLite-backed operations."""

import argparse
import logging
from collections.abc import Sequence

from album_maestro import specs
from album_maestro.commands import prompts
from album_maestro.commands.base import LibraryCommand
from album_maestro.library import Library, LibraryError
from album_maestro.models import Album, AlbumSummary, VARIOUS_ARTISTS

logger = logging.getLogger(__name__)


class CreateCommand(LibraryCommand):
    """Implement ``album-maestro create``."""

    name = "create"
    help = "Create a new album."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for creating an album."""
        pass

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        title = prompts.text("Album title")
        artist = prompts.text("Album artist (optional)")
        composer = prompts.text("Album composer (optional)")
        genre = prompts.text("Album genre")
        reference_url = prompts.text("Album reference URL (optional)")
        file_source = prompts.text(
            "Album file source (filename under sources/, optional)"
        )

        try:
            reference = library.create_album(
                Album(
                    title=title,
                    artist=artist or None,
                    composer=composer or None,
                    genre=genre,
                    url=reference_url or None,
                    file_source=file_source or None,
                    tracks=(),
                )
            )
        except (LibraryError, ValueError) as error:
            logger.error("Cannot create album: %s", error)
            return 1

        print(f"\nAlbum created: {reference}")
        print("The album has no tracks yet. Use 'edit' to add tracks.")
        return 0


class ListCommand(LibraryCommand):
    """Implement ``album-maestro list``."""

    name = "list"
    help = "List albums in a music library."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments for listing albums."""

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        try:
            albums = library.list_albums()
        except LibraryError as error:
            logger.error("Cannot list albums: %s", error)
            return 1
        _print_album_table(albums)
        return 0


class SearchCommand(LibraryCommand):
    """Implement ``album-maestro search``."""

    name = "search"
    help = "Search album metadata."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("--title", help="Match album titles")
        parser.add_argument("--artist", help="Match album artists")
        parser.add_argument("--composer", help="Match composers")
        parser.add_argument("--genre", help="Match genres")

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        try:
            albums = library.search_albums(
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


class ShowCommand(LibraryCommand):
    """Implement ``album-maestro show``."""

    name = "show"
    help = "Show an album and its tracks."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        try:
            album = library.load_album(args.reference)
        except LibraryError as error:
            logger.error("Cannot show album: %s", error)
            return 1

        print(f"Title:          {album.title}")
        print(f"Artist:         {album.artist or VARIOUS_ARTISTS}")
        print(f"Album artist:   {album.resolved_album_artist()}")
        print(f"Composer:       {album.composer or '—'}")
        print(f"Genre:          {album.genre}")
        print()
        print(f"Reference URL:  {album.url or '—'}")
        print(f"File source:    {album.file_source or '—'}")
        print()
        print("TRACKS")
        if not album.tracks:
            print("  No tracks yet.")
            return 0

        print("  #  TITLE                                      START    END")
        for position, track in enumerate(album.tracks, start=1):
            print(
                f"{position:>3}  {track.title:<42} "
                f"{specs.format_timestamp(track.start_ms):<8} "
                f"{specs.format_timestamp(track.end_ms)}"
            )
        return 0


class EditCommand(LibraryCommand):
    """Implement the interactive ``album-maestro edit`` command."""

    name = "edit"
    help = "Edit an album and its tracks."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        try:
            album = library.load_album(args.reference)
            library.update_album(
                args.reference,
                title=prompts.text("Album title", album.title),
                artist=prompts.text("Album artist (optional)", album.artist),
                composer=prompts.text("Album composer (optional)", album.composer),
                genre=prompts.text("Album genre", album.genre),
                url=prompts.text("Album reference URL (optional)", album.url),
                file_source=prompts.text(
                    "Album file source (filename under sources/, optional)",
                    album.file_source,
                ),
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
                    self._add_track(library, args.reference)
                elif action in {"e", "edit"}:
                    self._edit_track(library, args.reference)
                elif action in {"r", "remove"}:
                    self._remove_track(library, args.reference)
                else:
                    print("Please choose add, edit, remove, or done.")
            except (LibraryError, ValueError) as error:
                logger.error("Cannot edit track: %s", error)
                return 1

    def _add_track(self, library: Library, reference: str) -> None:
        """Prompt for and append one track."""

        album = library.load_album(reference)
        title = prompts.text("Track title")
        artist = prompts.override_text("Track artist (optional)", album.artist)
        composer = prompts.override_text("Track composer (optional)", album.composer)
        genre = prompts.override_text("Track genre (optional)", album.genre)
        url = prompts.override_text("Track reference URL (optional)", album.url)
        file_source = prompts.override_text(
            "Track file source (filename under sources/, optional)",
            album.file_source,
        )
        start_ms = self._prompt_timestamp("Track start (optional)")
        end_ms = self._prompt_timestamp("Track end (optional)")
        position = library.create_track(
            reference,
            title=title,
            artist=artist,
            composer=composer,
            genre=genre,
            url=url,
            file_source=file_source,
            start_ms=start_ms,
            end_ms=end_ms,
        )
        print(f"Added track {position}.")

    def _edit_track(self, library: Library, reference: str) -> None:
        """Prompt for and update one existing track."""

        album = library.load_album(reference)
        if not album.tracks:
            print("No tracks found.")
            return
        position = prompts.bounded_number("Track number", 1, len(album.tracks))
        track = album.tracks[position - 1]
        library.update_track(
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
            url=prompts.override_text(
                "Track reference URL (optional)", track.url or album.url
            ),
            file_source=prompts.override_text(
                "Track file source (filename under sources/, optional)",
                track.file_source or album.file_source,
            ),
            start_ms=self._prompt_timestamp("Track start (optional)", track.start_ms),
            end_ms=self._prompt_timestamp("Track end (optional)", track.end_ms),
        )
        print(f"Updated track {position}.")

    @staticmethod
    def _remove_track(library: Library, reference: str) -> None:
        """Prompt for and delete one existing track."""

        album = library.load_album(reference)
        if not album.tracks:
            print("No tracks found.")
            return
        position = prompts.bounded_number("Track number", 1, len(album.tracks))
        if prompts.confirm(f"Remove track {position}?", default=False):
            library.delete_track(reference, position)
            print(f"Removed track {position}.")

    @staticmethod
    def _prompt_timestamp(label: str, default_ms: int | None = None) -> int | None:
        """Prompt for a timestamp, retrying malformed values."""

        default = specs.format_timestamp(default_ms) if default_ms is not None else None
        while True:
            value = prompts.text(label, default)
            if not value:
                return None
            try:
                return specs.parse_timestamp(value)
            except ValueError:
                print("Please enter a timestamp such as 1:23 or 1:02:03.")


class DeleteCommand(LibraryCommand):
    """Implement the ``album-maestro delete`` command."""

    name = "delete"
    help = "Delete an album."

    def configure_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("reference", metavar="ALBUM")

    def run_library(self, library: Library, args: argparse.Namespace) -> int:
        reference = args.reference
        try:
            library.delete_album(reference)
            logger.info("Deleted album: %s", reference)
        except (LibraryError, ValueError) as error:
            logger.error("Cannot delete album: %s", error)
            return 1

        return 0


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
    print(
        "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    )
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
