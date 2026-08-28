import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_maestro.models import Chapter, TrackRequest
from yt_maestro.pipelines.album import (
    PipelineError,
    download_track,
    resolve_chapters,
    resolve_time_range,
)


class PipelineTests(unittest.TestCase):
    @patch("yt_maestro.pipelines.album.shutil.move")
    @patch(
        "yt_maestro.pipelines.album.audio.add_chapters",
        return_value="chaptered.m4a",
    )
    @patch(
        "yt_maestro.pipelines.album.audio.add_metadata",
        return_value="metadata.m4a",
    )
    @patch("yt_maestro.pipelines.album.audio.trim_audio", return_value="trimmed.m4a")
    @patch("yt_maestro.pipelines.album.audio.audio_duration_ms", return_value=20_000)
    @patch("yt_maestro.pipelines.album.downloader.download_audio")
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
            track = TrackRequest(
                url="https://example.com",
                title="Track",
                artist="Performer",
                album_artist="Various Artists",
                album="Album",
                start_ms=1_000,
                end_ms=10_000,
                chapters=(Chapter(1_000, "Opening"),),
            )

            result = download_track(track, output_dir)

        expected = (
            Path(output_dir).resolve() / "Various Artists" / "Album" / "downloaded.m4a"
        )
        self.assertEqual(result, expected)
        download_audio.assert_called_once()
        audio_duration_ms.assert_called_once()
        trim_audio.assert_called_once()
        add_metadata.assert_called_once()
        add_chapters.assert_called_once()
        move.assert_called_once_with("chaptered.m4a", result)

    def test_resolves_default_time_range(self):
        self.assertEqual(resolve_time_range(_track_request(), 10_000), (0, 10_000))

    def test_rejects_range_outside_recording(self):
        track = _track_request(end_ms=11_000)
        with self.assertRaisesRegex(PipelineError, "outside"):
            resolve_time_range(track, 10_000)

    def test_resolves_chapters_relative_to_trim(self):
        chapters = resolve_chapters(
            (Chapter(10_000, "One"), Chapter(15_000)),
            audio_start_ms=10_000,
            audio_end_ms=20_000,
        )
        self.assertEqual(chapters[0].start_ms, 0)
        self.assertEqual(chapters[0].end_ms, 5_000)
        self.assertEqual(chapters[1].title, "Chapter 2")
        self.assertEqual(chapters[1].end_ms, 10_000)


def _track_request(**overrides) -> TrackRequest:
    values = {
        "url": "url",
        "title": "Track",
        "artist": "Artist",
        "album_artist": "Artist",
        "album": "Album",
    }
    values.update(overrides)
    return TrackRequest(**values)


if __name__ == "__main__":
    unittest.main()
