import unittest

from yt_maestro.models import ChapterSpec, TrackSpec
from yt_maestro.spec import (
    SpecError,
    parse_specs,
    parse_timestamp,
    resolve_chapters,
    resolve_time_range,
)


class ParseSpecsTests(unittest.TestCase):
    def test_parses_and_normalizes_track(self):
        tracks = parse_specs(
            [
                {
                    "url": " https://example.com/watch?v=1 ",
                    "composer": " Johann Sebastian Bach ",
                    "start": "1:02.5",
                    "chapters": [
                        {"start": "1:30", "title": " Second "},
                        {"start": "1:02.5", "title": " First "},
                    ],
                }
            ]
        )

        track = tracks[0]
        self.assertEqual(track.url, "https://example.com/watch?v=1")
        self.assertEqual(track.start_ms, 62_500)
        self.assertEqual(
            [chapter.title for chapter in track.chapters], ["First", "Second"]
        )
        self.assertEqual(track.metadata()["artist"], "Johann Sebastian Bach")
        self.assertEqual(track.metadata()["album"], "Bach")

    def test_reports_track_number_for_invalid_track(self):
        with self.assertRaisesRegex(SpecError, "track 2: 'url'"):
            parse_specs([{"url": "https://example.com"}, {"url": ""}])

    def test_rejects_duplicate_chapter_starts(self):
        with self.assertRaisesRegex(SpecError, "must be unique"):
            parse_specs(
                [
                    {
                        "url": "https://example.com",
                        "chapters": [{"start": "1"}, {"start": "1.0"}],
                    }
                ]
            )


class TimestampTests(unittest.TestCase):
    def test_supported_timestamp_forms(self):
        self.assertEqual(parse_timestamp("1.25"), 1_250)
        self.assertEqual(parse_timestamp("02:03.5"), 123_500)
        self.assertEqual(parse_timestamp("1:02:03"), 3_723_000)

    def test_rejects_non_finite_timestamp(self):
        with self.assertRaises(SpecError):
            parse_timestamp("nan")


class ResolutionTests(unittest.TestCase):
    def test_resolves_default_time_range(self):
        self.assertEqual(resolve_time_range(TrackSpec(url="url"), 10_000), (0, 10_000))

    def test_rejects_range_outside_recording(self):
        track = TrackSpec(url="url", end_ms=11_000)
        with self.assertRaisesRegex(SpecError, "outside"):
            resolve_time_range(track, 10_000)

    def test_resolves_chapters_relative_to_trim(self):
        chapters = resolve_chapters(
            (ChapterSpec(10_000, "One"), ChapterSpec(15_000)),
            start_ms=10_000,
            end_ms=20_000,
        )
        self.assertEqual(chapters[0].start_ms, 0)
        self.assertEqual(chapters[0].end_ms, 5_000)
        self.assertEqual(chapters[1].title, "Chapter 2")
        self.assertEqual(chapters[1].end_ms, 10_000)


if __name__ == "__main__":
    unittest.main()
