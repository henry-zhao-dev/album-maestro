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


if __name__ == "__main__":
    unittest.main()
