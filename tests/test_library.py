import json
import tempfile
import unittest
from pathlib import Path

from yt_maestro.library import Library, LibraryError
from yt_maestro.specs import SpecError


class InitializeLibraryTests(unittest.TestCase):
    def test_creates_library(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            music_library = Library(root=root, name="My Music")
            manifest = music_library.initialize()

            self.assertEqual(manifest, root.resolve() / "yt-maestro.json")
            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8")),
                {
                    "kind": "library",
                    "name": "My Music",
                },
            )
            self.assertTrue((root / "albums").is_dir())
            self.assertTrue((root / "artists").is_dir())
            self.assertTrue((root / "downloads").is_dir())

    def test_refuses_to_replace_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            manifest = root / "yt-maestro.json"
            manifest.write_text("existing", encoding="utf-8")

            with self.assertRaisesRegex(LibraryError, "already exists"):
                Library(root=root, name="Music").initialize()

            self.assertEqual(manifest.read_text(encoding="utf-8"), "existing")


class LoadLibraryTests(unittest.TestCase):
    def test_loads_fixed_paths_and_ignores_schema_version(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "yt-maestro.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "kind": "library",
                        "name": "Music",
                    }
                ),
                encoding="utf-8",
            )
            for directory in ("albums", "artists", "downloads"):
                (root / directory).mkdir()

            music_library = Library.load(root)

        self.assertEqual(music_library.root, root.resolve())
        self.assertEqual(music_library.albums_dir, root.resolve() / "albums")
        self.assertEqual(music_library.artists_dir, root.resolve() / "artists")
        self.assertEqual(music_library.downloads_dir, root.resolve() / "downloads")

    def test_rejects_incomplete_library_structure(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "yt-maestro.json").write_text(
                json.dumps({"kind": "library", "name": "Music"}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(LibraryError, "albums directory"):
                Library.load(root)

    def test_rejects_noncanonical_catalog_references(self):
        music_library = Library(root=".", name="Music")

        for reference in ("Symphony-No-5", "symphony_no_5", "Symphony No. 5"):
            with self.subTest(reference=reference):
                with self.assertRaisesRegex(SpecError, "lowercase kebab-case"):
                    music_library.load_album(reference)


class CatalogMutationTests(unittest.TestCase):
    def test_creates_artist_with_normalized_reference_and_genre(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()

            reference = music_library.create_artist(
                " Beethoven's Lunch ", default_genre=" Jazz "
            )

            artist = json.loads(
                (root / "artists" / f"{reference}.json").read_text(encoding="utf-8")
            )

        self.assertEqual(reference, "beethovens-lunch")
        self.assertEqual(
            artist,
            {"name": "Beethoven's Lunch", "default_genre": "Jazz"},
        )

    def test_updates_artist_default_genre(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            (root / "artists" / "beethoven.json").write_text(
                json.dumps(
                    {
                        "name": "Ludwig van Beethoven",
                        "default_genre": "Classical",
                    }
                ),
                encoding="utf-8",
            )

            music_library.update_artist_default_genre("beethoven", " Jazz ")

            artist = json.loads(
                (root / "artists" / "beethoven.json").read_text(encoding="utf-8")
            )

        self.assertEqual(artist["default_genre"], "Jazz")

    def test_creates_album_with_genre_override_and_shared_url(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            (root / "artists" / "beethoven.json").write_text(
                json.dumps(
                    {
                        "name": "Ludwig van Beethoven",
                        "default_genre": "Classical",
                    }
                ),
                encoding="utf-8",
            )

            album_path = music_library.create_album(
                " Symphony No. 5 ",
                "beethoven",
                genre=" Jazz ",
                shared_url=" https://example.com/full ",
            )

            album = json.loads(album_path.read_text(encoding="utf-8"))

        self.assertEqual(album_path, root.resolve() / "albums" / "symphony-no-5.json")
        self.assertEqual(
            album,
            {
                "title": "Symphony No. 5",
                "artist": "beethoven",
                "genre": "Jazz",
                "url": "https://example.com/full",
                "tracks": [],
            },
        )


if __name__ == "__main__":
    unittest.main()
