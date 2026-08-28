import subprocess
import unittest
from unittest.mock import patch

from yt_maestro import audio
from yt_maestro.models import Chapter


class DurationTests(unittest.TestCase):
    @patch("yt_maestro.audio.subprocess.check_output", return_value="12.3456\n")
    def test_duration_is_reported_in_milliseconds(self, check_output):
        self.assertEqual(audio.audio_duration_ms("recording.m4a"), 12_345)
        self.assertEqual(check_output.call_args.args[0][0], "ffprobe")

    @patch("yt_maestro.audio.subprocess.check_output", return_value="nan")
    def test_invalid_duration_returns_zero(self, _check_output):
        self.assertEqual(audio.audio_duration_ms("recording.m4a"), 0)


class CommandFailureTests(unittest.TestCase):
    @patch("yt_maestro.audio.subprocess.check_output")
    def test_metadata_failure_returns_input_path(self, check_output):
        check_output.side_effect = subprocess.CalledProcessError(1, "ffmpeg", "bad")
        result = audio.add_metadata("input.m4a", "output.m4a", {"artist": "Bach"})
        self.assertEqual(result, "input.m4a")


class MetadataEscapingTests(unittest.TestCase):
    def test_chapter_metadata_is_escaped(self):
        tag = audio._chapter_tag(Chapter(0, "A=B; C#", 1000))
        self.assertIn("TITLE=A\\=B\\; C\\#", tag)


if __name__ == "__main__":
    unittest.main()
