import unittest

from album_maestro.specs import SpecError
from album_maestro.specs.catalog import _parse_album, dump_album
from album_maestro.specs.parsing import format_timestamp, parse_timestamp


class AlbumTests(unittest.TestCase):
    def test_dump_album_preserves_editable_specification_shape(self):
        album = _parse_album(
            {
                "title": "Album",
                "artist": "Artist",
                "composer": "Composer",
                "genre": "Classical",
                "url": "https://example.com/full",
                "tracks": [
                    {
                        "title": "Opening",
                        "start": "1:02.500",
                        "chapters": [{"start": "1:03", "title": "Theme"}],
                    }
                ],
            }
        )

        exported = dump_album(album)
        self.assertEqual(
            list(exported), ["title", "artist", "composer", "genre", "url", "tracks"]
        )
        self.assertEqual(
            exported,
            {
                "title": "Album",
                "artist": "Artist",
                "composer": "Composer",
                "genre": "Classical",
                "url": "https://example.com/full",
                "tracks": [
                    {
                        "title": "Opening",
                        "start": "1:02.500",
                        "chapters": [{"start": "1:03", "title": "Theme"}],
                    }
                ],
            },
        )

    def test_resolves_album_defaults_and_track_overrides(self):
        album = _parse_album(
            {
                "title": "Symphony No. 5",
                "artist": "Frankfurt Radio Symphony Orchestra",
                "composer": "Ludwig van Beethoven",
                "genre": "Classical",
                "url": "https://example.com/full",
                "tracks": [
                    {"title": "I. Allegro", "start": "0:04", "end": "8:30"},
                    {
                        "title": "II. Andante",
                        "artist": "Guest Orchestra",
                        "composer": "Another Composer",
                        "genre": "Romantic",
                        "url": "https://example.com/other",
                        "start": "8:30",
                    },
                ],
            }
        )

        tracks = album.requests()

        self.assertEqual(
            album.resolved_album_artist(), "Frankfurt Radio Symphony Orchestra"
        )
        self.assertEqual(tracks[0].url, "https://example.com/full")
        self.assertEqual(tracks[0].artist, "Frankfurt Radio Symphony Orchestra")
        self.assertEqual(tracks[0].composer, "Ludwig van Beethoven")
        self.assertEqual(tracks[0].genre, "Classical")
        self.assertEqual(tracks[0].track_number, 1)
        self.assertEqual(tracks[0].track_total, 2)
        self.assertEqual(tracks[0].metadata()["track"], "1/2")
        self.assertEqual(tracks[1].artist, "Guest Orchestra")
        self.assertEqual(tracks[1].album_artist, "Frankfurt Radio Symphony Orchestra")
        self.assertEqual(tracks[1].composer, "Another Composer")
        self.assertEqual(tracks[1].genre, "Romantic")
        self.assertEqual(tracks[1].start_ms, 510_000)

    def test_defaults_compilation_to_various_artists(self):
        album = _parse_album(
            {
                "title": "Best of Romantic",
                "artist": None,
                "genre": "Classical",
                "tracks": [
                    {"title": "Brahms", "artist": "Johannes Brahms", "url": "one"},
                    {"title": "Schubert", "artist": "Franz Schubert", "url": "two"},
                ],
            }
        )

        tracks = album.requests()

        self.assertEqual(
            [track.artist for track in tracks], ["Johannes Brahms", "Franz Schubert"]
        )
        self.assertEqual(
            [track.album_artist for track in tracks], ["Various Artists"] * 2
        )

    def test_missing_track_artist_also_uses_various_artists(self):
        album = _parse_album(
            {
                "title": "Composer Collection",
                "composer": "Johann Sebastian Bach",
                "genre": "Baroque",
                "tracks": [{"title": "Prelude", "url": "https://example.com"}],
            }
        )

        track = album.requests()[0]

        self.assertEqual(track.artist, "Various Artists")
        self.assertEqual(track.album_artist, "Various Artists")
        self.assertEqual(track.composer, "Johann Sebastian Bach")
        self.assertEqual(track.genre, "Baroque")

    def test_rejects_track_without_any_url(self):
        with self.assertRaisesRegex(
            SpecError, r"album\.tracks\[0\]: 'url' is a required property"
        ):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "Artist",
                    "genre": "Pop",
                    "tracks": [{"title": "Song"}],
                }
            )

    def test_rejects_album_without_genre(self):
        with self.assertRaisesRegex(SpecError, "album: .*genre.*required property"):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "Artist",
                    "tracks": [{"title": "Song", "url": "url"}],
                }
            )

    def test_accepts_display_names_for_all_credits(self):
        album = _parse_album(
            {
                "title": "Ocean Eyes",
                "artist": "Owl City",
                "genre": "Pop",
                "tracks": [
                    {
                        "title": "Cave In",
                        "artist": "Owl City feat. Someone",
                        "composer": "Adam Young",
                        "genre": "Synth-pop",
                        "url": "https://example.com",
                    }
                ],
            }
        )
        self.assertEqual(
            album.requests()[0].metadata()["artist"], "Owl City feat. Someone"
        )

    def test_schema_rejects_unknown_nested_fields(self):
        with self.assertRaisesRegex(
            SpecError, r"album\.tracks\[0\]\.chapters\[0\]: Additional properties"
        ):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "Artist",
                    "genre": "Classical",
                    "url": "https://example.com",
                    "tracks": [
                        {
                            "title": "Song",
                            "chapters": [{"start": "0:00", "end": "1:00"}],
                        }
                    ],
                }
            )

    def test_album_schema_rejects_unknown_fields(self):
        with self.assertRaisesRegex(SpecError, "album: Additional properties"):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "Artist",
                    "genre": "Pop",
                    "url": "https://example.com",
                    "tracks": [{"title": "Song"}],
                    "release_year": 2026,
                }
            )


class TimestampTests(unittest.TestCase):
    def test_formats_timestamps_for_specs_and_cli(self):
        self.assertEqual(format_timestamp(1_250), "0:01.250")
        self.assertEqual(format_timestamp(3_723_000), "1:02:03")
        self.assertEqual(format_timestamp(None), "—")

    def test_supported_timestamp_forms(self):
        self.assertEqual(parse_timestamp("1.25"), 1_250)
        self.assertEqual(parse_timestamp("02:03.5"), 123_500)
        self.assertEqual(parse_timestamp("1:02:03"), 3_723_000)

    def test_rejects_non_finite_timestamp(self):
        with self.assertRaises(SpecError):
            parse_timestamp("nan")


if __name__ == "__main__":
    unittest.main()
