import unittest
from pathlib import Path

from album_maestro import specs


class ExampleConfigurationTests(unittest.TestCase):
    def test_example_album_files_are_valid(self):
        examples = Path(__file__).parents[1] / "examples"

        for path in (examples / "albums").glob("*.json"):
            with self.subTest(path=path):
                specs.load_album(path)


if __name__ == "__main__":
    unittest.main()
