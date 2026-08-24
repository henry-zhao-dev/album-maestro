import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_maestro.cli import main


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


if __name__ == "__main__":
    unittest.main()
