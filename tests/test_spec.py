import json
import tempfile
import unittest
from pathlib import Path

from yt_maestro.models import Artist
from yt_maestro.specs import SpecError, load_album
from yt_maestro.specs._parsing import parse_timestamp
from yt_maestro.specs.catalog import _parse_album, _parse_artist


class AlbumTests(unittest.TestCase):
    def test_resolves_shared_url_into_numbered_track_requests(self):
        artist = Artist("Ludwig van Beethoven", "Classical")
        album = _parse_album(
            {
                "title": "Symphony No. 5",
                "artist": "beethoven",
                "url": "https://example.com/full",
                "tracks": [
                    {"title": "I. Allegro", "start": "0:04", "end": "8:30"},
                    {"title": "II. Andante", "start": "8:30"},
                ],
            },
            {"beethoven": artist},
        )

        tracks = album.requests()

        self.assertIs(album.album_artist, artist)
        self.assertEqual(tracks[0].url, "https://example.com/full")
        self.assertEqual(tracks[0].track_number, 1)
        self.assertEqual(tracks[0].track_total, 2)
        self.assertEqual(tracks[0].metadata()["track"], "1/2")
        self.assertEqual(tracks[1].start_ms, 510_000)

    def test_supports_a_different_url_for_each_track(self):
        album = _parse_album(
            {
                "title": "Songs",
                "artist": "artist",
                "tracks": [
                    {"title": "One", "url": "https://example.com/one"},
                    {"title": "Two", "url": "https://example.com/two"},
                ],
            },
            {"artist": Artist("Artist")},
        )

        self.assertEqual(
            [track.url for track in album.requests()],
            ["https://example.com/one", "https://example.com/two"],
        )

    def test_resolves_track_artists_for_a_compilation(self):
        album = _parse_album(
            {
                "title": "Best of Romantic",
                "artist": "various-artists",
                "tracks": [
                    {
                        "title": "Brahms",
                        "artist": "brahms",
                        "url": "https://example.com/brahms",
                    },
                    {
                        "title": "Schubert",
                        "artist": "schubert",
                        "url": "https://example.com/schubert",
                    },
                ],
            },
            {
                "various-artists": Artist("Various Artists"),
                "brahms": Artist("Johannes Brahms"),
                "schubert": Artist("Franz Schubert"),
            },
        )

        tracks = album.requests()

        self.assertEqual(
            [track.artist for track in tracks],
            ["Johannes Brahms", "Franz Schubert"],
        )
        self.assertEqual(tracks[0].album_artist, "Various Artists")
        self.assertEqual(tracks[0].metadata()["album_artist"], "Various Artists")

    def test_loads_artist_reference_from_directory(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            artists = root / "artists"
            artists.mkdir()
            (artists / "beethoven.json").write_text(
                json.dumps(
                    {
                        "name": "Ludwig van Beethoven",
                        "default_genre": "Classical",
                    }
                ),
                encoding="utf-8",
            )
            album_path = root / "symphony.json"
            album_path.write_text(
                json.dumps(
                    {
                        "title": "Symphony",
                        "artist": "beethoven",
                        "tracks": [{"title": "Movement", "url": "https://example.com"}],
                    }
                ),
                encoding="utf-8",
            )

            album = load_album(album_path, artists)

        self.assertEqual(album.album_artist.name, "Ludwig van Beethoven")
        self.assertEqual(album.requests()[0].genre, "Classical")

    def test_rejects_a_track_without_any_url(self):
        with self.assertRaisesRegex(
            SpecError, r"album\.tracks\[0\]: 'url' is a required property"
        ):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "artist",
                    "tracks": [{"title": "Song"}],
                },
                {"artist": Artist("Artist")},
            )

    def test_rejects_noncanonical_artist_reference(self):
        with self.assertRaisesRegex(SpecError, r"album\.artist: .*does not match"):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "Example Artist",
                    "url": "https://example.com",
                    "tracks": [{"title": "Song"}],
                },
                {"Example Artist": Artist("Example Artist")},
            )

    def test_schema_rejects_unknown_nested_fields(self):
        with self.assertRaisesRegex(
            SpecError, r"album\.tracks\[0\]\.chapters\[0\]: Additional properties"
        ):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "artist",
                    "url": "https://example.com",
                    "tracks": [
                        {
                            "title": "Song",
                            "chapters": [{"start": "0:00", "end": "1:00"}],
                        }
                    ],
                },
                {"artist": Artist("Artist")},
            )

    def test_album_schema_rejects_unknown_fields(self):
        with self.assertRaisesRegex(SpecError, "album: Additional properties"):
            _parse_album(
                {
                    "title": "Album",
                    "artist": "artist",
                    "url": "https://example.com",
                    "tracks": [{"title": "Song"}],
                    "release_year": 2026,
                },
                {"artist": Artist("Artist")},
            )

    def test_artist_schema_rejects_unknown_fields(self):
        with self.assertRaisesRegex(SpecError, "artist: Additional properties"):
            _parse_artist({"name": "Artist", "genre": "Classical"})


class TimestampTests(unittest.TestCase):
    def test_supported_timestamp_forms(self):
        self.assertEqual(parse_timestamp("1.25"), 1_250)
        self.assertEqual(parse_timestamp("02:03.5"), 123_500)
        self.assertEqual(parse_timestamp("1:02:03"), 3_723_000)

    def test_rejects_non_finite_timestamp(self):
        with self.assertRaises(SpecError):
            parse_timestamp("nan")


if __name__ == "__main__":
    unittest.main()
