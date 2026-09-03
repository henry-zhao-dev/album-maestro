import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import call, patch

from album_maestro.cli import main
from album_maestro.library import Library


class HelpTests(unittest.TestCase):
    def test_no_arguments_prints_root_help(self):
        output = StringIO()
        with redirect_stdout(output):
            result = main([])
        self.assertEqual(result, 0)
        self.assertIn("Create a new music library.", output.getvalue())
        self.assertIn("Work with albums in a music library.", output.getvalue())

    def test_help_after_command_is_handled_by_command_parser(self):
        for arguments, usage, detail in (
            (["init", "-h"], "usage: album-maestro init", "--name"),
            (["album", "-h"], "usage: album-maestro album", "download"),
        ):
            with self.subTest(command=arguments[0]):
                output = StringIO()
                with redirect_stdout(output), self.assertRaises(SystemExit) as context:
                    main(arguments)
                self.assertEqual(context.exception.code, 0)
                self.assertIn(usage, output.getvalue())
                self.assertIn(detail, output.getvalue())

    def test_missing_album_command_uses_a_user_facing_name(self):
        errors = StringIO()
        with redirect_stderr(errors), self.assertRaises(SystemExit) as context:
            main(["album"])
        self.assertEqual(context.exception.code, 2)
        self.assertIn("the following arguments are required: COMMAND", errors.getvalue())
        self.assertNotIn("album_operation", errors.getvalue())


class InitCommandTests(unittest.TestCase):
    def test_init_uses_directory_name_by_default(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "collection"
            result = main(["init", str(root)])
            self.assertEqual(result, 0)
            config = json.loads((root / "album-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["name"], "collection")


class AlbumCommandTests(unittest.TestCase):
    @patch("builtins.input", side_effect=("Best of Romantic Era", "", "", "Classical", ""))
    def test_create_supports_compilation_without_album_artist(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            result = main(["album", "create", "--library", str(root)])
            album = json.loads((root / "albums" / "best-of-romantic-era.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 0)
        self.assertEqual(album, {"title": "Best of Romantic Era", "artist": None, "genre": "Classical", "tracks": []})

    @patch("builtins.input", side_effect=("Bach Violin Partita No. 3", "Hilary Hahn", "Johann Sebastian Bach", "Baroque", "https://youtu.be/recording"))
    def test_create_writes_literal_metadata(self, input_mock):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            output = StringIO()
            with redirect_stdout(output):
                result = main(["album", "create", "--library", str(root)])
            album = json.loads((root / "albums" / "bach-violin-partita-no-3.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 0)
        self.assertEqual(
            input_mock.call_args_list,
            [call("Album title: "), call("Album artist (optional): "), call("Album composer (optional): "), call("Album genre: "), call("Album shared URL (optional): ")],
        )
        self.assertEqual(album["artist"], "Hilary Hahn")
        self.assertEqual(album["composer"], "Johann Sebastian Bach")
        self.assertEqual(album["genre"], "Baroque")

    @patch("builtins.input", side_effect=("No Genre Album", "Artist", "", "", ""))
    def test_create_rejects_missing_genre(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            result = main(["album", "create", "--library", str(root)])
            self.assertFalse((root / "albums" / "no-genre-album.json").exists())
        self.assertEqual(result, 1)

    @patch("album_maestro.commands.album.pipeline.download_album")
    def test_download_loads_album_from_library(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]
            result = main(["album", "download", "symphony", "--library", str(root)])
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
            result = main(["album", "download", "symphony", "--library", str(root)])
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
            result = main(["album", "download", "--all", "--library", str(root)])
        self.assertEqual(result, 0)
        self.assertEqual(download_album.call_count, 2)
        self.assertEqual([call.args[0].title for call in download_album.call_args_list], ["Concerto", "Symphony"])


def _create_album_library(root: Path) -> None:
    Library(root=root, name="Music").initialize()
    _write_album(root, "symphony", "Symphony")


def _write_album(root: Path, reference: str, title: str) -> None:
    (root / "albums" / f"{reference}.json").write_text(
        json.dumps(
            {
                "title": title,
                "artist": "Ludwig van Beethoven",
                "composer": "Ludwig van Beethoven",
                "genre": "Classical",
                "url": "https://example.com/full",
                "tracks": [
                    {"title": "First", "start": "0", "end": "1:00"},
                    {"title": "Second", "start": "1:00"},
                ],
            }
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
