import unittest
from pathlib import Path

from yt_maestro import specs


class ExampleConfigurationTests(unittest.TestCase):
    def test_example_artist_and_album_files_are_valid(self):
        examples = Path(__file__).parents[1] / "examples"
        artists_dir = examples / "artists"

        for path in artists_dir.glob("*.json"):
            with self.subTest(path=path):
                specs.load_artist(path)

        for path in (examples / "albums").glob("*.json"):
            with self.subTest(path=path):
                specs.load_album(path, artists_dir)


if __name__ == "__main__":
    unittest.main()
