import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from yt_maestro.cli import main
from yt_maestro.library import Library


class HelpTests(unittest.TestCase):
    def test_no_arguments_prints_root_help(self):
        output = StringIO()

        with redirect_stdout(output):
            result = main([])

        self.assertEqual(result, 0)
        self.assertIn("Create a new music library.", output.getvalue())
        self.assertIn("Work with albums in a music library.", output.getvalue())

    def test_help_after_command_is_handled_by_command_parser(self):
        cases = (
            (["init", "-h"], "usage: yt-maestro init", "--name"),
            (["album", "-h"], "usage: yt-maestro album", "download"),
        )

        for arguments, usage, detail in cases:
            with self.subTest(command=arguments[0]):
                output = StringIO()
                with (
                    redirect_stdout(output),
                    self.assertRaises(SystemExit) as exit_context,
                ):
                    main(arguments)

                self.assertEqual(exit_context.exception.code, 0)
                self.assertIn(usage, output.getvalue())
                self.assertIn(detail, output.getvalue())

    def test_missing_album_command_uses_a_user_facing_name(self):
        errors = StringIO()

        with redirect_stderr(errors), self.assertRaises(SystemExit) as exit_context:
            main(["album"])

        self.assertEqual(exit_context.exception.code, 2)
        self.assertIn(
            "the following arguments are required: COMMAND", errors.getvalue()
        )
        self.assertNotIn("album_operation", errors.getvalue())


class InitCommandTests(unittest.TestCase):
    def test_init_uses_directory_name_by_default(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "collection"

            result = main(["init", str(root)])

            self.assertEqual(result, 0)
            config = json.loads((root / "yt-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["name"], "collection")

    def test_init_accepts_library_name(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            result = main(["init", str(root), "--name", "My Library"])

            self.assertEqual(result, 0)
            config = json.loads((root / "yt-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["name"], "My Library")


class AlbumCommandTests(unittest.TestCase):
    @patch("yt_maestro.commands.album.pipeline.download_album")
    def test_download_loads_album_from_library(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(["album", "download", "symphony", "--library", str(root)])

        self.assertEqual(result, 0)
        album, destination = download_album.call_args.args
        self.assertEqual(album.title, "Symphony")
        self.assertEqual(album.album_artist.name, "Ludwig van Beethoven")
        self.assertEqual(destination, root.resolve() / "downloads")

    @patch("yt_maestro.commands.album.pipeline.download_album")
    @patch("yt_maestro.commands.album.prompts.confirm", return_value=False)
    def test_download_confirms_before_overwriting(self, confirm, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            existing = (
                root / "downloads" / "Ludwig van Beethoven" / "Symphony" / "First.m4a"
            )
            existing.parent.mkdir(parents=True)
            existing.touch()

            result = main(["album", "download", "symphony", "--library", str(root)])

        self.assertEqual(result, 0)
        confirm.assert_called_once_with(
            "Continue and overwrite existing tracks?", default=False
        )
        download_album.assert_not_called()

    @patch("yt_maestro.commands.album.pipeline.download_album")
    @patch("yt_maestro.commands.album.prompts.confirm")
    def test_overwrite_option_skips_confirmation(self, confirm, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            existing = (
                root / "downloads" / "Ludwig van Beethoven" / "Symphony" / "First.m4a"
            )
            existing.parent.mkdir(parents=True)
            existing.touch()
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(
                [
                    "album",
                    "download",
                    "symphony",
                    "--library",
                    str(root),
                    "--overwrite",
                ]
            )

        self.assertEqual(result, 0)
        confirm.assert_not_called()
        download_album.assert_called_once()

    @patch("yt_maestro.commands.album.pipeline.download_album")
    def test_download_reports_missing_album(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            Library(root=root, name="Music").initialize()

            result = main(["album", "download", "missing", "--library", str(root)])

        self.assertEqual(result, 1)
        download_album.assert_not_called()

    @patch("yt_maestro.commands.album.pipeline.download_album")
    def test_download_accepts_multiple_album_references(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            _write_album(root, "concerto", "Concerto")
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(
                [
                    "album",
                    "download",
                    "symphony",
                    "concerto",
                    "--library",
                    str(root),
                ]
            )

        self.assertEqual(result, 0)
        self.assertEqual(download_album.call_count, 2)
        self.assertEqual(
            [call.args[0].title for call in download_album.call_args_list],
            ["Symphony", "Concerto"],
        )

    @patch("yt_maestro.commands.album.pipeline.download_album")
    def test_download_all_uses_every_album_file(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            _write_album(root, "concerto", "Concerto")
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(["album", "download", "--all", "--library", str(root)])

        self.assertEqual(result, 0)
        self.assertEqual(download_album.call_count, 2)
        self.assertEqual(
            [call.args[0].title for call in download_album.call_args_list],
            ["Concerto", "Symphony"],
        )


def _create_album_library(root: Path) -> None:
    Library(root=root, name="Music").initialize()
    (root / "artists" / "beethoven.json").write_text(
        json.dumps(
            {
                "name": "Ludwig van Beethoven",
                "default_genre": "Classical",
            }
        ),
        encoding="utf-8",
    )
    _write_album(root, "symphony", "Symphony")


def _write_album(root: Path, reference: str, title: str) -> None:
    (root / "albums" / f"{reference}.json").write_text(
        json.dumps(
            {
                "title": title,
                "artist": "beethoven",
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
