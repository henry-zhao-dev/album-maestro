import unittest
from pathlib import Path

from album_maestro import specs


class ExampleSpecificationTests(unittest.TestCase):
    def test_example_album_files_are_valid(self):
        examples = Path(__file__).parents[1] / "examples"

        for path in (examples / "albums").glob("*.json"):
            with self.subTest(path=path):
                specs.load_album(path)

    def test_example_album_source_references_are_filenames(self):
        examples = Path(__file__).parents[1] / "examples"

        for path in (examples / "albums").glob("*.json"):
            album = specs.load_album(path)
            for track in album.requests():
                with self.subTest(path=path, source=track.file_source):
                    self.assertIsNotNone(track.file_source)
                    assert track.file_source is not None
                    source = Path(track.file_source)
                    self.assertEqual(source.name, track.file_source)
                    self.assertIn(source.suffix.lower(), {".ogg", ".mp3"})


if __name__ == "__main__":
    unittest.main()
