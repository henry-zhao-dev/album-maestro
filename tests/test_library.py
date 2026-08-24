import json
import tempfile
import unittest
from pathlib import Path

from yt_maestro.library import LibraryConfig, LibraryError, initialize


class InitializeLibraryTests(unittest.TestCase):
    def test_creates_git_friendly_library(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"

            manifest = initialize(root, LibraryConfig(name="My Music"))

            self.assertEqual(manifest, root.resolve() / "yt-maestro.json")
            self.assertEqual(
                json.loads(manifest.read_text(encoding="utf-8")),
                {
                    "schema_version": 1,
                    "kind": "library",
                    "name": "My Music",
                    "paths": {
                        "albums": "albums",
                        "artists": "artists",
                        "downloads": "downloads",
                    },
                },
            )
            self.assertTrue((root / "albums" / ".gitkeep").exists())
            self.assertTrue((root / "artists" / ".gitkeep").exists())
            self.assertTrue((root / "downloads").is_dir())
            self.assertEqual(
                (root / ".gitignore").read_text(encoding="utf-8"),
                "# yt-maestro generated files\n/downloads/\n/.yt-maestro/\n",
            )

    def test_preserves_existing_gitignore(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / ".gitignore").write_text(".DS_Store\n", encoding="utf-8")

            initialize(root, LibraryConfig(name="Music", downloads_dir=Path("output")))

            self.assertEqual(
                (root / ".gitignore").read_text(encoding="utf-8"),
                ".DS_Store\n# yt-maestro generated files\n/output/\n/.yt-maestro/\n",
            )

    def test_refuses_to_replace_existing_manifest(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            manifest = root / "yt-maestro.json"
            manifest.write_text("existing", encoding="utf-8")

            with self.assertRaisesRegex(LibraryError, "already exists"):
                initialize(root, LibraryConfig(name="Music"))

            self.assertEqual(manifest.read_text(encoding="utf-8"), "existing")

    def test_rejects_paths_outside_library(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            with self.assertRaisesRegex(LibraryError, "relative path"):
                initialize(
                    temporary_dir,
                    LibraryConfig(name="Music", downloads_dir=Path("../downloads")),
                )


if __name__ == "__main__":
    unittest.main()
