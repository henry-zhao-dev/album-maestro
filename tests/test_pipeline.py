import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from album_maestro.models import Chapter, TrackRequest
from album_maestro.pipeline import (
    PipelineError,
    create_track,
    _resolve_chapters,
    _resolve_time_range,
    _track_output_path,
)


class PipelineTests(unittest.TestCase):
    def test_output_path_rejects_path_traversal(self):
        track = _track_request(title="../outside")

        with tempfile.TemporaryDirectory() as output_dir:
            with self.assertRaisesRegex(PipelineError, "path separator"):
                _track_output_path(track, Path(output_dir), ".m4a")

    def test_output_path_rejects_windows_path_separators(self):
        track = _track_request(title="folder\\outside")

        with tempfile.TemporaryDirectory() as output_dir:
            with self.assertRaisesRegex(PipelineError, "path separator"):
                _track_output_path(track, Path(output_dir), ".m4a")

    def test_output_path_preserves_safe_display_names(self):
        track = _track_request(title="Track 01 — Finale")

        with tempfile.TemporaryDirectory() as output_dir:
            result = _track_output_path(track, Path(output_dir), ".m4a")

        self.assertEqual(result.name, "Track 01 — Finale.m4a")
        self.assertEqual(result.parent.name, "Album")

    def test_output_path_rejects_symlinked_directory_outside_destination(self):
        track = _track_request()

        with (
            tempfile.TemporaryDirectory() as output_dir,
            tempfile.TemporaryDirectory() as outside_dir,
        ):
            destination = Path(output_dir)
            (destination / "Artist").symlink_to(outside_dir, target_is_directory=True)

            with self.assertRaisesRegex(PipelineError, "escapes"):
                _track_output_path(track, destination, ".m4a")

    @patch("album_maestro.pipeline.shutil.move")
    @patch("album_maestro.pipeline.shutil.copy2")
    @patch(
        "album_maestro.pipeline.audio.add_chapters",
        return_value="chaptered.m4a",
    )
    @patch(
        "album_maestro.pipeline.audio.add_metadata",
        return_value="metadata.m4a",
    )
    @patch("album_maestro.pipeline.audio.trim_audio", return_value="trimmed.m4a")
    @patch("album_maestro.pipeline.audio.audio_duration_ms", return_value=20_000)
    def test_runs_processing_stages_in_order(
        self,
        audio_duration_ms,
        trim_audio,
        add_metadata,
        add_chapters,
        copy2,
        move,
    ):
        with tempfile.TemporaryDirectory() as output_dir:
            root = Path(output_dir)
            source = root / "source.m4a"
            destination = root / "library"
            work_dir = root / "work"
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

            result = create_track(track, source, destination, work_dir)

        expected = destination.resolve() / "Various Artists" / "Album" / "Track.m4a"
        self.assertEqual(result, expected)
        copy2.assert_called_once_with(source, work_dir / "Track.m4a")
        audio_duration_ms.assert_called_once()
        trim_audio.assert_called_once()
        add_metadata.assert_called_once()
        add_chapters.assert_called_once()
        move.assert_called_once_with("chaptered.m4a", result)

    def test_resolves_default_time_range(self):
        self.assertEqual(_resolve_time_range(_track_request(), 10_000), (0, 10_000))

    def test_rejects_range_outside_recording(self):
        track = _track_request(end_ms=11_000)
        with self.assertRaisesRegex(PipelineError, "outside"):
            _resolve_time_range(track, 10_000)

    def test_resolves_chapters_relative_to_trim(self):
        chapters = _resolve_chapters(
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
