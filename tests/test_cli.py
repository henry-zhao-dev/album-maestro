import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import call, patch

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
    @patch(
        "builtins.input",
        side_effect=("Bach Album", "bach", "2", "", ""),
    )
    def test_create_selects_from_multiple_matching_artists(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist_file(root, "bach-cpe", "C.P.E. Bach")
            _write_artist_file(root, "bach-js", "Johann Sebastian Bach")
            output = StringIO()

            with redirect_stdout(output):
                result = main(["album", "create", "--library", str(root)])

            album = json.loads(
                (root / "albums" / "bach-album.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        self.assertEqual(album["artist"], "bach-js")
        self.assertIn("1. C.P.E. Bach", output.getvalue())
        self.assertIn("2. Johann Sebastian Bach", output.getvalue())

    @patch(
        "builtins.input",
        side_effect=(
            "Beethoven Symphony No. 5",
            "Ludwig Van Beethoven",
            "",
            "https://youtu.be/link-to-symphony",
        ),
    )
    def test_create_writes_an_album_draft(self, input_mock):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist(root)
            output = StringIO()

            with redirect_stdout(output):
                result = main(["album", "create", "--library", str(root)])

            album_path = root / "albums" / "beethoven-symphony-no-5.json"
            album = json.loads(album_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(
            input_mock.call_args_list,
            [
                call("Album title: "),
                call("Album artist: "),
                call("Album genre (optional) [Classical]: "),
                call("Album shared URL (optional): "),
            ],
        )
        self.assertEqual(
            album,
            {
                "title": "Beethoven Symphony No. 5",
                "artist": "beethoven",
                "url": "https://youtu.be/link-to-symphony",
                "tracks": [],
            },
        )
        self.assertIn(
            "Album created at albums/beethoven-symphony-no-5.json",
            output.getvalue(),
        )
        self.assertIn("You can edit JSON to create tracks.", output.getvalue())

    @patch(
        "builtins.input",
        side_effect=(
            "Not Beethoven's Work",
            "Beethoven's Lunch",
            "Jazz",
            "https://example.com",
        ),
    )
    def test_create_writes_an_unknown_artist_with_the_entered_genre(self, input_mock):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist(root)
            output = StringIO()

            with redirect_stdout(output):
                result = main(["album", "create", "--library", str(root)])

            album_path = root / "albums" / "not-beethovens-work.json"
            artist_path = root / "artists" / "beethovens-lunch.json"
            album = json.loads(album_path.read_text(encoding="utf-8"))
            artist = json.loads(artist_path.read_text(encoding="utf-8"))

        self.assertEqual(result, 0)
        self.assertEqual(
            input_mock.call_args_list,
            [
                call("Album title: "),
                call("Album artist: "),
                call("Album genre (optional): "),
                call("Album shared URL (optional): "),
            ],
        )
        self.assertEqual(
            artist,
            {"name": "Beethoven's Lunch", "default_genre": "Jazz"},
        )
        self.assertEqual(album["artist"], "beethovens-lunch")
        self.assertNotIn("genre", album)

    @patch(
        "builtins.input",
        side_effect=("Jazz Album", "Ludwig van Beethoven", "Jazz", ""),
    )
    @patch("yt_maestro.commands.album.prompts.confirm", return_value=False)
    def test_create_keeps_a_changed_genre_as_an_album_override(self, confirm, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist(root)

            result = main(["album", "create", "--library", str(root)])

            album = json.loads(
                (root / "albums" / "jazz-album.json").read_text(encoding="utf-8")
            )
            artist = json.loads(
                (root / "artists" / "beethoven.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        confirm.assert_called_once_with(
            "Set 'Jazz' as the default genre for Ludwig van Beethoven?",
            default=False,
        )
        self.assertEqual(artist["default_genre"], "Classical")
        self.assertEqual(album["genre"], "Jazz")

    @patch(
        "builtins.input",
        side_effect=("Jazz Album", "Ludwig van Beethoven", "Jazz", ""),
    )
    @patch("yt_maestro.commands.album.prompts.confirm", return_value=True)
    def test_create_updates_an_existing_artists_default_genre(self, confirm, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist(root)

            result = main(["album", "create", "--library", str(root)])

            album = json.loads(
                (root / "albums" / "jazz-album.json").read_text(encoding="utf-8")
            )
            artist = json.loads(
                (root / "artists" / "beethoven.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        confirm.assert_called_once()
        self.assertEqual(artist["default_genre"], "Jazz")
        self.assertNotIn("genre", album)

    @patch(
        "builtins.input",
        side_effect=("No Genre Album", "Ludwig van Beethoven", "", ""),
    )
    @patch("yt_maestro.commands.album.prompts.confirm")
    def test_create_accepts_no_genre_for_an_existing_artist_without_a_default(
        self, confirm, input_mock
    ):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            _write_artist(root, default_genre=None)

            result = main(["album", "create", "--library", str(root)])

            album = json.loads(
                (root / "albums" / "no-genre-album.json").read_text(encoding="utf-8")
            )
            artist = json.loads(
                (root / "artists" / "beethoven.json").read_text(encoding="utf-8")
            )

        self.assertEqual(result, 0)
        self.assertIn(call("Album genre (optional): "), input_mock.call_args_list)
        confirm.assert_not_called()
        self.assertNotIn("default_genre", artist)
        self.assertNotIn("genre", album)

    @patch("builtins.input", return_value="Existing Album")
    def test_create_does_not_replace_an_existing_album(self, _input):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            Library(root=root, name="Music").initialize()
            album_path = root / "albums" / "existing-album.json"
            album_path.write_text("existing", encoding="utf-8")

            with self.assertLogs("yt_maestro.commands.album", level="ERROR"):
                result = main(["album", "create", "--library", str(root)])

            contents = album_path.read_text(encoding="utf-8")

        self.assertEqual(result, 1)
        self.assertEqual(contents, "existing")

    @patch("yt_maestro.commands.album.pipeline.download_album")
    def test_download_loads_album_from_library(self, download_album):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            download_album.return_value = [Path("first.m4a"), Path("second.m4a")]

            result = main(["album", "download", "symphony", "--library", str(root)])

        self.assertEqual(result, 0)
        album, destination, overwrite = download_album.call_args.args
        self.assertEqual(album.title, "Symphony")
        self.assertEqual(album.album_artist.name, "Ludwig van Beethoven")
        self.assertEqual(destination, root.resolve() / "downloads")
        self.assertFalse(overwrite)

    @patch("yt_maestro.commands.album.pipeline.download_album")
    @patch("yt_maestro.commands.album.prompts.confirm", return_value=False)
    def test_download_skips_existing_tracks_when_overwrite_declined(
        self, confirm, download_album
    ):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            _create_album_library(root)
            existing = (
                root / "downloads" / "Ludwig van Beethoven" / "Symphony" / "First.m4a"
            )
            existing.parent.mkdir(parents=True)
            existing.touch()
            download_album.return_value = [existing, Path("second.m4a")]

            result = main(["album", "download", "symphony", "--library", str(root)])

        self.assertEqual(result, 0)
        confirm.assert_called_once_with("Overwrite existing tracks?", default=False)
        album, destination, overwrite = download_album.call_args.args
        self.assertEqual(album.title, "Symphony")
        self.assertEqual(destination, root.resolve() / "downloads")
        self.assertFalse(overwrite)

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
        album, destination, overwrite = download_album.call_args.args
        self.assertEqual(album.title, "Symphony")
        self.assertEqual(destination, root.resolve() / "downloads")
        self.assertTrue(overwrite)

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
    _write_artist(root)
    _write_album(root, "symphony", "Symphony")


def _write_artist(root: Path, default_genre: str | None = "Classical") -> None:
    _write_artist_file(root, "beethoven", "Ludwig van Beethoven", default_genre)


def _write_artist_file(
    root: Path,
    reference: str,
    name: str,
    default_genre: str | None = "Classical",
) -> None:
    data = {"name": name}
    if default_genre is not None:
        data["default_genre"] = default_genre

    (root / "artists" / f"{reference}.json").write_text(
        json.dumps(data),
        encoding="utf-8",
    )


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
