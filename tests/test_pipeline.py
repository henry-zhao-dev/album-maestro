import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_maestro.models import ChapterSpec, TrackSpec
from yt_maestro.pipeline import process_track


class PipelineTests(unittest.TestCase):
    @patch("yt_maestro.pipeline.shutil.move")
    @patch("yt_maestro.pipeline.audio.add_chapters", return_value="chaptered.m4a")
    @patch("yt_maestro.pipeline.audio.add_metadata", return_value="metadata.m4a")
    @patch("yt_maestro.pipeline.audio.trim_audio", return_value="trimmed.m4a")
    @patch("yt_maestro.pipeline.audio.audio_duration_ms", return_value=20_000)
    @patch("yt_maestro.pipeline.downloader.download_audio")
    def test_runs_processing_stages_in_order(
        self,
        download_audio,
        audio_duration_ms,
        trim_audio,
        add_metadata,
        add_chapters,
        move,
    ):
        with tempfile.TemporaryDirectory() as output_dir:
            download_audio.return_value = Path(output_dir) / "downloaded.m4a"
            track = TrackSpec(
                url="https://example.com",
                artist="Performer",
                album="Album",
                start_ms=1_000,
                end_ms=10_000,
                chapters=(ChapterSpec(1_000, "Opening"),),
            )

            result = process_track(track, output_dir)

        expected = Path(output_dir).resolve() / "Performer" / "Album" / "downloaded.m4a"
        self.assertEqual(result, expected)
        download_audio.assert_called_once()
        audio_duration_ms.assert_called_once()
        trim_audio.assert_called_once()
        add_metadata.assert_called_once()
        add_chapters.assert_called_once()
        move.assert_called_once_with("chaptered.m4a", result)


if __name__ == "__main__":
    unittest.main()
