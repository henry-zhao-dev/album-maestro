import json
import tempfile
import unittest
from pathlib import Path

from album_maestro.library import Library, LibraryError
from album_maestro.specs import SpecError


class InitializeLibraryTests(unittest.TestCase):
    def test_creates_library_without_an_artist_catalog(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"
            manifest = Library(root=root, name="My Music").initialize()

            self.assertEqual(manifest, root.resolve() / "album-maestro.json")
            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8")),
                {"kind": "library", "name": "My Music"},
            )
            self.assertTrue((root / "albums").is_dir())
            self.assertFalse((root / "artists").exists())
            self.assertTrue((root / "downloads").is_dir())

    def test_refuses_to_replace_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            manifest = root / "album-maestro.json"
            manifest.write_text("existing", encoding="utf-8")
            with self.assertRaisesRegex(LibraryError, "already exists"):
                Library(root=root, name="Music").initialize()
            self.assertEqual(manifest.read_text(encoding="utf-8"), "existing")


class LoadLibraryTests(unittest.TestCase):
    def test_loads_fixed_paths_and_ignores_schema_version(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "album-maestro.json").write_text(
                json.dumps({"schema_version": 1, "kind": "library", "name": "Music"}),
                encoding="utf-8",
            )
            for directory in ("albums", "downloads"):
                (root / directory).mkdir()
            music_library = Library.load(root)

        self.assertEqual(music_library.root, root.resolve())
        self.assertEqual(music_library.albums_dir, root.resolve() / "albums")
        self.assertEqual(music_library.downloads_dir, root.resolve() / "downloads")

    def test_rejects_incomplete_library_structure(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "album-maestro.json").write_text(
                json.dumps({"kind": "library", "name": "Music"}), encoding="utf-8"
            )
            with self.assertRaisesRegex(LibraryError, "albums directory"):
                Library.load(root)

    def test_rejects_noncanonical_album_references(self):
        music_library = Library(root=".", name="Music")
        for reference in ("Symphony-No-5", "symphony_no_5", "Symphony No. 5"):
            with self.subTest(reference=reference):
                with self.assertRaisesRegex(SpecError, "lowercase kebab-case"):
                    music_library.load_album(reference)


class CatalogMutationTests(unittest.TestCase):
    def test_creates_album_with_literal_metadata_and_shared_url(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            album_path = music_library.create_album(
                " Symphony No. 5 ",
                " Frankfurt Radio Symphony Orchestra ",
                composer=" Ludwig van Beethoven ",
                genre=" Classical ",
                shared_url=" https://example.com/full ",
            )
            album = json.loads(album_path.read_text(encoding="utf-8"))

        self.assertEqual(album_path, root.resolve() / "albums" / "symphony-no-5.json")
        self.assertEqual(
            album,
            {
                "title": "Symphony No. 5",
                "artist": "Frankfurt Radio Symphony Orchestra",
                "composer": "Ludwig van Beethoven",
                "genre": "Classical",
                "url": "https://example.com/full",
                "tracks": [],
            },
        )

    def test_creates_compilation_album_with_optional_artist_and_composer(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            album_path = music_library.create_album(
                "Best of Romantic Era", None, composer="", genre="Classical"
            )
            album = json.loads(album_path.read_text(encoding="utf-8"))

        self.assertEqual(album["artist"], None)
        self.assertEqual(album["genre"], "Classical")
        self.assertNotIn("composer", album)
        self.assertEqual(album["tracks"], [])

    def test_rejects_blank_genre(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            with self.assertRaisesRegex(LibraryError, "genre"):
                library.create_album("Album", "Artist", genre=" ")


if __name__ == "__main__":
    unittest.main()
