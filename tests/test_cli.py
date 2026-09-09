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
        self.assertIn(
            "Turn recordings into albums you can keep and play.", output.getvalue()
        )
        self.assertIn("Initialize a library directory.", output.getvalue())
        self.assertIn("Create an album interactively.", output.getvalue())
        self.assertIn("Import album specifications from JSON.", output.getvalue())

    def test_help_after_command_is_handled_by_command_parser(self):
        for arguments, usage, detail in (
            (["init", "-h"], "usage: album-maestro init", "--name"),
            (["create", "-h"], "usage: album-maestro create", "--library"),
            (["process", "-h"], "usage: album-maestro process", "--output"),
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

            result = main(["import", "--json", str(source), "--library", str(root)])
            album = Library.load(root).load_album("imported-album")

        self.assertEqual(result, 0)
        self.assertEqual(album.tracks[0].start_ms, 1_000)
        self.assertEqual(album.tracks[0].end_ms, 5_000)

    def test_imports_album_and_track_sources_into_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            (library.sources_path / "album.m4a").write_bytes(b"album audio")
            (library.sources_path / "opening.m4a").write_bytes(b"track audio")
            source = Path(temporary_dir) / "album.json"
            source.write_text(
                '{"title":"Imported Album","genre":"Classical",'
                '"file_source":"album.m4a","tracks":[{"title":"Opening",'
                '"file_source":"opening.m4a"}]}',
                encoding="utf-8",
            )

            result = main(["import", "--json", str(source), "--library", str(root)])
            album = Library.load(root).load_album("imported-album")

        self.assertEqual(result, 0)
        self.assertEqual(album.file_source, "sources/album.m4a")
        self.assertEqual(album.tracks[0].file_source, "sources/opening.m4a")

    def test_import_directory_overwrites_existing_album(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            library = Library.load(root)
            library.create_album(
                Album(title="Album", artist="Old Artist", genre="Pop", tracks=())
            )
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


class ProcessCommandTests(unittest.TestCase):
    @patch("album_maestro.commands.process.pipeline.create_track")
    def test_process_uses_local_source_without_downloading(self, create_track):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            source = library.sources_path / "recording.m4a"
            source.write_bytes(b"audio")
            library.create_album(
                Album(
                    title="Album",
                    artist="Artist",
                    genre="Classical",
                    file_source="recording.m4a",
                    tracks=(AlbumTrack(title="Opening"),),
                )
            )
            output = root / "tracks"
            create_track.return_value = output / "Artist" / "Album" / "Opening.m4a"

            result = main(["process", "album", "--library", str(root)])

        self.assertEqual(result, 0)
        create_track.assert_called_once()
        request, resolved_source, destination, work_dir = create_track.call_args.args
        self.assertIsNone(request.url)
        self.assertEqual(request.file_source, "sources/recording.m4a")
        self.assertEqual(resolved_source, source.resolve())
        self.assertEqual(destination, output.resolve())
        self.assertFalse(work_dir.exists())

    @patch("album_maestro.commands.process.pipeline.create_track")
    def test_process_continues_after_one_track_fails(self, create_track):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            (library.sources_path / "recording.m4a").write_bytes(b"audio")
            library.create_album(
                Album(
                    title="Album",
                    artist="Artist",
                    genre="Classical",
                    file_source="recording.m4a",
                    tracks=(
                        AlbumTrack(title="Opening"),
                        AlbumTrack(title="Second"),
                    ),
                )
            )
            create_track.side_effect = [RuntimeError("broken source"), Path("done")]

            result = main(["process", "album", "--library", str(root)])

        self.assertEqual(result, 1)
        self.assertEqual(create_track.call_count, 2)


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
                    tracks=(AlbumTrack(title="Opening", start_ms=1_000, end_ms=5_000),),
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

    def test_exports_album_and_track_sources(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            (library.sources_path / "album.m4a").write_bytes(b"album audio")
            (library.sources_path / "opening.m4a").write_bytes(b"track audio")
            library.create_album(
                Album(
                    title="Album",
                    artist=None,
                    genre="Classical",
                    url="https://example.com/album",
                    file_source="album.m4a",
                    tracks=(
                        AlbumTrack(
                            title="Opening",
                            url="https://example.com/opening",
                            file_source="opening.m4a",
                        ),
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
        self.assertEqual(exported["url"], "https://example.com/album")
        self.assertEqual(exported["file_source"], "sources/album.m4a")
        self.assertEqual(exported["tracks"][0]["url"], "https://example.com/opening")
        self.assertEqual(exported["tracks"][0]["file_source"], "sources/opening.m4a")

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
    @patch(
        "builtins.input",
        side_effect=("Best of Romantic Era", "", "", "Classical", "", ""),
    )
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

    @patch(
        "builtins.input",
        side_effect=(
            "Bach Violin Partita No. 3",
            "Hilary Hahn",
            "Johann Sebastian Bach",
            "Baroque",
            "https://example.com/recording",
            "",
        ),
    )
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
            [
                call("Album title: "),
                call("Album artist (optional): "),
                call("Album composer (optional): "),
                call("Album genre: "),
                call("Album reference URL (optional): "),
                call("Album file source (filename under sources/, optional): "),
            ],
        )
        self.assertEqual(
            album,
            (
                "Bach Violin Partita No. 3",
                "Hilary Hahn",
                "Johann Sebastian Bach",
                "Baroque",
                "https://example.com/recording",
            ),
        )

    @patch(
        "builtins.input",
        side_effect=(
            "Bach Album",
            "Bach",
            "Johann Sebastian Bach",
            "Classical",
            "",
            "",
        ),
    )
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
            library.create_album(
                Album(
                    title="Beethoven Symphony",
                    artist="Ludwig van Beethoven",
                    genre="Classical",
                    tracks=(),
                )
            )
            library.create_album(
                Album(title="Ocean Eyes", artist="Owl City", genre="Pop", tracks=())
            )
            output = StringIO()
            with redirect_stdout(output):
                result = main(
                    ["search", "--artist", "Beethoven", "--library", str(root)]
                )

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
        self.assertIn("Title:          Symphony", output.getvalue())
        self.assertIn("Artist:         Ludwig van Beethoven", output.getvalue())
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
            "",
            "a",
            "Third",
            "",
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
        self.assertEqual(
            [track.title for track in album.tracks], ["First", "Second", "Third"]
        )
        self.assertEqual(album.tracks[-1].start_ms, 120_000)
        self.assertEqual(album.tracks[-1].end_ms, 180_000)
        self.assertIsNone(album.tracks[-1].artist)
        self.assertIsNone(album.tracks[-1].composer)
        self.assertIsNone(album.tracks[-1].genre)
        self.assertIsNone(album.tracks[-1].url)
        self.assertIsNone(album.tracks[-1].file_source)
        resolved_track = album.requests()[-1]
        self.assertEqual(resolved_track.artist, "Ludwig van Beethoven")
        self.assertEqual(resolved_track.composer, "Ludwig van Beethoven")
        self.assertEqual(resolved_track.genre, "Classical")
        self.assertEqual(resolved_track.url, "https://example.com/full")

    @patch(
        "builtins.input",
        side_effect=("No Genre Album", "Artist", "", "", "Classical", "", ""),
    )
    def test_create_retries_missing_genre(self, input_mock):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            output = StringIO()
            with redirect_stdout(output):
                result = main(["create", "--library", str(root)])
            with sqlite3.connect(root / "album-maestro.db") as connection:
                album = connection.execute(
                    "SELECT title, artist, genre, url FROM albums"
                ).fetchone()

        self.assertEqual(result, 0)
        self.assertEqual(
            input_mock.call_args_list,
            [
                call("Album title: "),
                call("Album artist (optional): "),
                call("Album composer (optional): "),
                call("Album genre: "),
                call("Album genre: "),
                call("Album reference URL (optional): "),
                call("Album file source (filename under sources/, optional): "),
            ],
        )
        self.assertEqual(
            album,
            ("No Genre Album", "Artist", "Classical", None),
        )
        self.assertIn("Album genre must be provided.", output.getvalue())


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
