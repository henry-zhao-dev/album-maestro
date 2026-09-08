import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import call, patch

from album_maestro.cli import main
from album_maestro.library import Library
from album_maestro.models import Album, AlbumTrack


class HelpTests(unittest.TestCase):
    def test_no_arguments_prints_root_help(self):
        output = StringIO()
        with redirect_stdout(output):
            result = main([])
        self.assertEqual(result, 0)
        self.assertIn("Create a new music library.", output.getvalue())
        self.assertIn("Create a new album.", output.getvalue())

    def test_help_after_command_is_handled_by_command_parser(self):
        for arguments, usage, detail in (
            (["init", "-h"], "usage: album-maestro init", "--name"),
            (["create", "-h"], "usage: album-maestro create", "--library"),
        ):
            with self.subTest(command=arguments[0]):
                output = StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as context:
                    main(arguments)
                self.assertEqual(context.exception.code, 0)
                self.assertIn(usage, output.getvalue())
                self.assertIn(detail, output.getvalue())


class InitCommandTests(unittest.TestCase):
    def test_init_uses_directory_name_by_default(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "collection"
            result = main(["init", str(root)])
            self.assertEqual(result, 0)
            with sqlite3.connect(root / "album-maestro.db") as connection:
                self.assertEqual(
                    connection.execute("SELECT name FROM library").fetchone(),
                    ("collection",),
                )


class ImportCommandTests(unittest.TestCase):
    def test_imports_one_json_album_into_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            source = Path(temporary_dir) / "album.json"
            source.write_text(
                '{"title":"Imported Album","artist":"Artist",'
                '"genre":"Classical","url":"https://example.com/source",'
                '"tracks":[{"title":"Opening","start":"0:01",'
                '"end":"0:05"}]}',
                encoding="utf-8",
            )

            result = main(
                ["import", "--json", str(source), "--library", str(root)]
            )
            album = Library.load(root).load_album("imported-album")

        self.assertEqual(result, 0)
        self.assertEqual(album.tracks[0].start_ms, 1_000)
        self.assertEqual(album.tracks[0].end_ms, 5_000)

    def test_import_directory_overwrites_existing_album(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            library = Library.load(root)
            library.create_album(Album(title="Album", artist="Old Artist", genre="Pop", tracks=()))
            library.create_track("album", title="Stale Track")
            source_dir = Path(temporary_dir) / "albums"
            source_dir.mkdir()
            (source_dir / "album.json").write_text(
                '{"title":"Album","artist":"New Artist",'
                '"genre":"Jazz","tracks":[{"title":"Fresh Track",'
                '"url":"https://example.com/source"}]}',
                encoding="utf-8",
            )

            result = main(
                [
                    "import",
                    "--directory",
                    str(source_dir),
                    "--library",
                    str(root),
                    "--overwrite",
                ]
            )
            album = Library.load(root).load_album("album")

        self.assertEqual(result, 0)
        self.assertEqual(album.artist, "New Artist")
        self.assertEqual([track.title for track in album.tracks], ["Fresh Track"])


class ExportCommandTests(unittest.TestCase):
    def test_exports_one_album_to_schema_compatible_json(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            library = Library.load(root)
            library.create_album(
                Album(
                    title="Album",
                    artist="Artist",
                    genre="Classical",
                    url="https://example.com/source",
                    tracks=(
                        AlbumTrack(title="Opening", start_ms=1_000, end_ms=5_000),
                    ),
                )
            )
            output = Path(temporary_dir) / "album.json"

            result = main(
                [
                    "export",
                    "album",
                    "--json",
                    str(output),
                    "--library",
                    str(root),
                ]
            )
            exported = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(exported["title"], "Album")
        self.assertEqual(exported["tracks"][0]["start"], "0:01")
        self.assertEqual(exported["tracks"][0]["end"], "0:05")

    def test_exports_all_albums_to_a_directory(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            library = Library.load(root)
            for title in ("Alpha", "Beta"):
                library.create_album(
                    Album(title=title, artist="Artist", genre="Pop", tracks=())
                )
            output_dir = Path(temporary_dir) / "albums"

            result = main(
                [
                    "export",
                    "--all",
                    "--directory",
                    str(output_dir),
                    "--library",
                    str(root),
                ]
            )
            exported_names = sorted(path.name for path in output_dir.glob("*.json"))

        self.assertEqual(result, 0)
        self.assertEqual(exported_names, ["alpha.json", "beta.json"])


class AlbumCommandTests(unittest.TestCase):
    @patch("builtins.input", side_effect=("Best of Romantic Era", "", "", "Classical", ""))
    def test_create_supports_compilation_without_album_artist(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            output = StringIO()
            with redirect_stdout(output):
                result = main(["create", "--library", str(root)])
            with sqlite3.connect(root / "album-maestro.db") as connection:
                album = connection.execute(
                    "SELECT title, artist, composer, genre, url FROM albums"
                ).fetchone()
        self.assertEqual(result, 0)
        self.assertIn("Album created: best-of-romantic-era", output.getvalue())
        self.assertEqual(album, ("Best of Romantic Era", None, None, "Classical", None))

    @patch("builtins.input", side_effect=("Bach Violin Partita No. 3", "Hilary Hahn", "Johann Sebastian Bach", "Baroque", "https://youtu.be/recording"))
    def test_create_writes_literal_metadata(self, input_mock):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            output = StringIO()
            with redirect_stdout(output):
                result = main(["create", "--library", str(root)])
            with sqlite3.connect(root / "album-maestro.db") as connection:
                album = connection.execute(
                    "SELECT title, artist, composer, genre, url FROM albums"
                ).fetchone()
        self.assertEqual(result, 0)
        self.assertEqual(
            input_mock.call_args_list,
            [call("Album title: "), call("Album artist (optional): "), call("Album composer (optional): "), call("Album genre: "), call("Album shared URL (optional): ")],
        )
        self.assertEqual(
            album,
            (
                "Bach Violin Partita No. 3",
                "Hilary Hahn",
                "Johann Sebastian Bach",
                "Baroque",
                "https://youtu.be/recording",
            ),
        )

    @patch("builtins.input", side_effect=("Bach Album", "Bach", "Johann Sebastian Bach", "Classical", ""))
    def test_list_prints_albums_from_sqlite(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            main(["create", "--library", str(root)])
            output = StringIO()
            with redirect_stdout(output):
                result = main(["list", "--library", str(root)])

        self.assertEqual(result, 0)
        self.assertIn("REFERENCE", output.getvalue())
        self.assertIn("bach-album", output.getvalue())
        self.assertIn("Bach", output.getvalue())
        self.assertIn("Classical", output.getvalue())
        self.assertIn("0", output.getvalue())

    def test_search_filters_by_artist(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            library.create_album(Album(title="Beethoven Symphony", artist="Ludwig van Beethoven", genre="Classical", tracks=()))
            library.create_album(Album(title="Ocean Eyes", artist="Owl City", genre="Pop", tracks=()))
            output = StringIO()
            with redirect_stdout(output):
                result = main(["search", "--artist", "Beethoven", "--library", str(root)])

        self.assertEqual(result, 0)
        self.assertIn("beethoven-symphony", output.getvalue())
        self.assertNotIn("ocean-eyes", output.getvalue())

    def test_show_displays_album_and_tracks_from_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            output = StringIO()
            with redirect_stdout(output):
                result = main(["show", "symphony", "--library", str(root)])

        self.assertEqual(result, 0)
        self.assertIn("Title:        Symphony", output.getvalue())
        self.assertIn("Artist:       Ludwig van Beethoven", output.getvalue())
        self.assertIn("First", output.getvalue())
        self.assertIn("Second", output.getvalue())

    def test_delete_removes_album_from_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)

            result = main(["delete", "symphony", "--library", str(root)])

            self.assertEqual(result, 0)
            self.assertEqual(Library.load(root).list_albums(), [])
            with sqlite3.connect(root / "album-maestro.db") as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM tracks").fetchone(),
                    (0,),
                )

    def test_delete_returns_failure_for_unknown_album(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)

            result = main(["delete", "missing", "--library", str(root)])

            self.assertEqual(result, 1)
            self.assertEqual(
                [album.reference for album in Library.load(root).list_albums()],
                ["symphony"],
            )

    @patch(
        "builtins.input",
        side_effect=(
            "",
            "",
            "",
            "",
            "",
            "a",
            "Third",
            "",
            "",
            "",
            "",
            "2:00",
            "3:00",
            "d",
        ),
    )
    def test_edit_adds_a_track_to_sqlite(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            result = main(["edit", "symphony", "--library", str(root)])
            album = Library.load(root).load_album("symphony")

        self.assertEqual(result, 0)
        self.assertEqual([track.title for track in album.tracks], ["First", "Second", "Third"])
        self.assertEqual(album.tracks[-1].start_ms, 120_000)
        self.assertEqual(album.tracks[-1].end_ms, 180_000)
        self.assertIsNone(album.tracks[-1].artist)
        self.assertIsNone(album.tracks[-1].composer)
        self.assertIsNone(album.tracks[-1].genre)
        self.assertIsNone(album.tracks[-1].url)
        resolved_track = album.requests()[-1]
        self.assertEqual(resolved_track.artist, "Ludwig van Beethoven")
        self.assertEqual(resolved_track.composer, "Ludwig van Beethoven")
        self.assertEqual(resolved_track.genre, "Classical")
        self.assertEqual(resolved_track.url, "https://example.com/full")

    @patch("builtins.input", side_effect=("No Genre Album", "Artist", "", "", ""))
    def test_create_rejects_missing_genre(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            result = main(["create", "--library", str(root)])
            with sqlite3.connect(root / "album-maestro.db") as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM albums").fetchone(),
                    (0,),
                )
        self.assertEqual(result, 1)

    @patch("album_maestro.commands.album.pipeline.download_album")
    def test_download_loads_album_from_library(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]
            result = main(["download", "symphony", "--library", str(root)])
        self.assertEqual(result, 0)
        album, destination, overwrite = download_album.call_args.args
        self.assertEqual(album.title, "Symphony")
        self.assertEqual(album.artist, "Ludwig van Beethoven")
        self.assertEqual(destination, root.resolve() / "downloads")
        self.assertFalse(overwrite)

    @patch("album_maestro.commands.album.pipeline.download_album")
    @patch("album_maestro.commands.album.prompts.confirm", return_value=False)
    def test_download_skips_existing_tracks_when_overwrite_declined(self, confirm, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            existing = root / "downloads" / "Ludwig van Beethoven" / "Symphony" / "First.m4a"
            existing.parent.mkdir(parents=True)
            existing.touch()
            download_album.return_value = [existing, Path("second.m4a")]
            result = main(["download", "symphony", "--library", str(root)])
        self.assertEqual(result, 0)
        confirm.assert_called_once_with("Overwrite existing tracks?", default=False)
        self.assertFalse(download_album.call_args.args[2])

    @patch("album_maestro.commands.album.pipeline.download_album")
    def test_download_all_uses_every_album_file(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            _write_album(root, "concerto", "Concerto")
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]
            result = main(["download", "--all", "--library", str(root)])
        self.assertEqual(result, 0)
        self.assertEqual(download_album.call_count, 2)
        self.assertEqual([call.args[0].title for call in download_album.call_args_list], ["Concerto", "Symphony"])


def _create_album_library(root: Path) -> None:
    Library(root=root, name="Music").initialize()
    _write_album(root, "symphony", "Symphony")


def _write_album(root: Path, reference: str, title: str) -> None:
    library = Library.load(root)
    reference_from_title = library.create_album(
        Album(
            title=title,
            artist="Ludwig van Beethoven",
            composer="Ludwig van Beethoven",
            genre="Classical",
            url="https://example.com/full",
            tracks=(),
        )
    )
    if reference_from_title != reference:
        raise AssertionError(
            f"expected reference {reference!r}, got {reference_from_title!r}"
        )
    library.create_track(
        reference,
        title="First",
        start_ms=0,
        end_ms=60_000,
    )
    library.create_track(reference, title="Second", start_ms=60_000)


if __name__ == "__main__":
    unittest.main()
