import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_maestro.cli import main
from yt_maestro.library import LibraryConfig, initialize


class InitCommandTests(unittest.TestCase):
    def test_non_interactive_init_uses_defaults(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "collection"

            result = main(["init", str(root), "--no-interaction"])

            self.assertEqual(result, 0)
            config = json.loads((root / "yt-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["name"], "collection")

    @patch("builtins.input", side_effect=["My Library", "", "", "audio", "yes"])
    def test_interactive_init_uses_answers(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            result = main(["init", str(root)])

            self.assertEqual(result, 0)
            config = json.loads((root / "yt-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["name"], "My Library")
            self.assertEqual(config["paths"]["downloads"], "audio")

    @patch("builtins.input", side_effect=["", "", "", "", "no"])
    def test_interactive_init_can_be_cancelled(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            result = main(["init", str(root)])

            self.assertEqual(result, 0)
            self.assertFalse(root.exists())

    @patch(
        "builtins.input",
        side_effect=["", "../albums", "records", "", "", "yes"],
    )
    def test_interactive_init_reprompts_for_invalid_path(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            result = main(["init", str(root)])

            self.assertEqual(result, 0)
            config = json.loads((root / "yt-maestro.json").read_text(encoding="utf-8"))
            self.assertEqual(config["paths"]["albums"], "records")


class AlbumCommandTests(unittest.TestCase):
    @patch("yt_maestro.commands.album.pipelines.download_album")
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

    @patch("yt_maestro.commands.album.pipelines.download_album")
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

    @patch("yt_maestro.commands.album.pipelines.download_album")
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

    @patch("yt_maestro.commands.album.pipelines.download_album")
    def test_download_reports_missing_album(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            initialize(root, LibraryConfig(name="Music"))

            result = main(["album", "download", "missing", "--library", str(root)])

        self.assertEqual(result, 1)
        download_album.assert_not_called()

    @patch("yt_maestro.commands.album.pipelines.download_album")
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

    @patch("yt_maestro.commands.album.pipelines.download_album")
    def test_download_all_uses_every_album_file(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            _write_album(root, "concerto", "Concerto")
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(
                ["album", "download", "--all", "--library", str(root)]
            )

        self.assertEqual(result, 0)
        self.assertEqual(download_album.call_count, 2)
        self.assertEqual(
            [call.args[0].title for call in download_album.call_args_list],
            ["Concerto", "Symphony"],
        )


def _create_album_library(root: Path) -> None:
    initialize(root, LibraryConfig(name="Music"))
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
