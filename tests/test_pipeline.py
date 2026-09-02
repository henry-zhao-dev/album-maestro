import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from album_maestro.models import Chapter, TrackRequest
from album_maestro.pipeline import (
    PipelineError,
    _download_track,
    _download_tracks,
    _resolve_chapters,
    _resolve_time_range,
)


class PipelineTests(unittest.TestCase):
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
    @patch("album_maestro.pipeline.downloader.download_audio")
    def test_runs_processing_stages_in_order(
        self,
        download_audio,
        audio_duration_ms,
        trim_audio,
        add_metadata,
        add_chapters,
        copy2,
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

            result = _download_track(track, output_dir)

        expected = (
            Path(output_dir).resolve() / "Various Artists" / "Album" / "Track.m4a"
        )
        self.assertEqual(result, expected)
        download_audio.assert_called_once()
        copy2.assert_called_once()
        audio_duration_ms.assert_called_once()
        trim_audio.assert_called_once()
        add_metadata.assert_called_once()
        add_chapters.assert_called_once()
        move.assert_called_once_with("chaptered.m4a", result)

    @patch("album_maestro.pipeline._create_track")
    @patch("album_maestro.pipeline.downloader.download_audio")
    def test_downloads_a_shared_source_once(self, download_audio, create_track):
        source = Path("source.m4a")
        download_audio.return_value = source
        create_track.side_effect = [Path("first.m4a"), Path("second.m4a")]
        tracks = (
            _track_request(title="First", url="https://example.com/shared"),
            _track_request(title="Second", url="https://example.com/shared"),
        )

        with (
            tempfile.TemporaryDirectory() as output_dir,
            self.assertLogs("album_maestro.pipeline", level="INFO") as logs,
        ):
            outputs = _download_tracks(tracks, output_dir)

        self.assertEqual(outputs, [Path("first.m4a"), Path("second.m4a")])
        download_audio.assert_called_once()
        self.assertEqual(
            [call.args[1] for call in create_track.call_args_list],
            [source, source],
        )
        messages = [record.getMessage() for record in logs.records]
        self.assertTrue(messages[0].startswith("Downloading source 1/1"))
        self.assertEqual(messages[2], "Creating track 1/2: First")
        self.assertEqual(messages[4], "Creating track 2/2: Second")

    @patch("album_maestro.pipeline._create_track")
    @patch("album_maestro.pipeline.downloader.download_audio")
    def test_skips_an_existing_track_without_overwrite(
        self, download_audio, create_track
    ):
        with tempfile.TemporaryDirectory() as output_dir:
            track = _track_request()
            existing = Path(output_dir).resolve() / "Artist" / "Album" / "Track.m4a"
            existing.parent.mkdir(parents=True)
            existing.write_text("existing", encoding="utf-8")

            result = _download_track(track, output_dir)

            self.assertEqual(result, existing)
            self.assertEqual(existing.read_text(encoding="utf-8"), "existing")
        download_audio.assert_not_called()
        create_track.assert_not_called()

    @patch(
        "album_maestro.pipeline.audio.add_metadata",
        side_effect=lambda source, output, metadata: source,
    )
    @patch("album_maestro.pipeline.audio.audio_duration_ms", return_value=10_000)
    @patch("album_maestro.pipeline.downloader.download_audio")
    def test_overwrites_an_existing_track(
        self, download_audio, audio_duration_ms, add_metadata
    ):
        with tempfile.TemporaryDirectory() as output_dir:
            root = Path(output_dir).resolve()
            source = root / "source.m4a"
            source.write_text("replacement", encoding="utf-8")
            download_audio.return_value = source

            track = _track_request()
            existing = root / "Artist" / "Album" / "Track.m4a"
            existing.parent.mkdir(parents=True)
            existing.write_text("existing", encoding="utf-8")

            result = _download_track(track, output_dir, overwrite=True)

            self.assertEqual(result, existing)
            self.assertEqual(existing.read_text(encoding="utf-8"), "replacement")
        download_audio.assert_called_once()
        audio_duration_ms.assert_called_once()
        add_metadata.assert_called_once()

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
