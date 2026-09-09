import sqlite3
import tempfile
import unittest
from pathlib import Path

from album_maestro.library import Library, LibraryError
from album_maestro.models import Album, AlbumTrack, Chapter


class InitializeLibraryTests(unittest.TestCase):
    def test_creates_sqlite_library(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"
            database_path = Library(root=root, name="My Music").initialize()

            self.assertEqual(database_path, root.resolve() / "album-maestro.db")
            self.assertTrue(database_path.is_file())
            self.assertFalse((root / "albums").exists())

            with sqlite3.connect(database_path) as connection:
                self.assertEqual(
                    connection.execute("SELECT name FROM library").fetchone(),
                    ("My Music",),
                )
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone(),
                    (2,),
                )
                self.assertIn(
                    "file_source",
                    {row[1] for row in connection.execute("PRAGMA table_info(albums)")},
                )
                self.assertIn(
                    "file_source",
                    {row[1] for row in connection.execute("PRAGMA table_info(tracks)")},
                )

    def test_refuses_to_replace_existing_database(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            database_path = root / "album-maestro.db"
            database_path.write_text("existing", encoding="utf-8")

            with self.assertRaisesRegex(LibraryError, "already exists"):
                Library(root=root, name="Music").initialize()

            self.assertEqual(database_path.read_text(encoding="utf-8"), "existing")


class LoadLibraryTests(unittest.TestCase):
    def test_loads_library_from_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            Library(root=root, name="Music").initialize()

            music_library = Library.load(root)

        self.assertEqual(music_library.root, root.resolve())
        self.assertEqual(
            music_library.database_path, root.resolve() / "album-maestro.db"
        )

    def test_rejects_incomplete_library_structure(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "album-maestro.db").touch()

            with self.assertRaisesRegex(LibraryError, "library"):
                Library.load(root)

    def test_load_migrates_an_older_database_with_no_chapters_table(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            database_path = root / "album-maestro.db"
            with sqlite3.connect(database_path) as connection:
                connection.executescript("""
                    CREATE TABLE library (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
                    CREATE TABLE albums (
                        id INTEGER PRIMARY KEY,
                        reference TEXT NOT NULL UNIQUE,
                        title TEXT NOT NULL,
                        artist TEXT,
                        composer TEXT,
                        genre TEXT NOT NULL,
                        url TEXT
                    );
                    CREATE TABLE tracks (
                        id INTEGER PRIMARY KEY,
                        album_id INTEGER NOT NULL,
                        position INTEGER NOT NULL,
                        title TEXT NOT NULL
                    );
                    INSERT INTO library (id, name) VALUES (1, 'Music');
                    """)

            Library.load(root)

            with sqlite3.connect(database_path) as connection:
                self.assertIsNotNone(
                    connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'chapters'"
                    ).fetchone()
                )
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone(),
                    (2,),
                )


class CatalogMutationTests(unittest.TestCase):
    def test_stores_relative_file_sources(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            source = library.sources_path / "recording.m4a"
            source.write_bytes(b"audio")

            library.create_album(
                Album(
                    title="Album",
                    artist="Artist",
                    genre="Classical",
                    file_source="sources/recording.m4a",
                    tracks=(),
                )
            )
            loaded = library.load_album("album")

        self.assertEqual(loaded.file_source, "sources/recording.m4a")

    def test_prepends_sources_to_bare_file_names(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            (library.sources_path / "recording.m4a").write_bytes(b"audio")

            library.create_album(
                Album(
                    title="Album",
                    artist="Artist",
                    genre="Classical",
                    file_source="recording.m4a",
                    tracks=(),
                )
            )
            loaded = library.load_album("album")

        self.assertEqual(loaded.file_source, "sources/recording.m4a")

    def test_resolves_existing_file_source_to_library_path(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            source = library.sources_path / "recording.m4a"
            source.write_bytes(b"audio")

            resolved = library.resolve_file_source("recording.m4a")

        self.assertEqual(resolved, source.resolve())

    def test_rejects_file_sources_outside_sources_directory(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "library"
            library = Library(root=root, name="Music")
            library.initialize()
            (root / "outside.m4a").write_bytes(b"audio")

            with self.assertRaisesRegex(LibraryError, "inside the sources directory"):
                library.create_album(
                    Album(
                        title="Album",
                        artist="Artist",
                        genre="Classical",
                        file_source="../outside.m4a",
                        tracks=(),
                    )
                )

    def test_creates_album_in_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()

            reference = music_library.create_album(
                Album(
                    title=" Symphony No. 5 ",
                    artist=" Ludwig van Beethoven ",
                    composer=" Ludwig van Beethoven ",
                    genre=" Classical ",
                    url=" https://example.com/full ",
                    tracks=(),
                )
            )

            album = music_library.load_album(reference)

        self.assertEqual(reference, "symphony-no-5")
        self.assertEqual(album.title, "Symphony No. 5")
        self.assertEqual(album.artist, "Ludwig van Beethoven")
        self.assertEqual(album.composer, "Ludwig van Beethoven")
        self.assertEqual(album.genre, "Classical")
        self.assertEqual(album.tracks, ())

    def test_lists_albums_in_title_order_with_track_counts(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            music_library.create_album(
                Album(title="Zeta", artist=None, genre="Classical", tracks=())
            )
            music_library.create_album(
                Album(title="Alpha", artist="Artist", genre="Pop", tracks=())
            )

            with sqlite3.connect(music_library.database_path) as connection:
                album_id = connection.execute(
                    "SELECT id FROM albums WHERE title = 'Alpha'"
                ).fetchone()[0]
                connection.execute(
                    "INSERT INTO tracks (album_id, position, title) VALUES (?, ?, ?)",
                    (album_id, 1, "Track One"),
                )

            albums = music_library.list_albums()

        self.assertEqual([album.title for album in albums], ["Alpha", "Zeta"])
        self.assertEqual(albums[0].track_count, 1)
        self.assertEqual(albums[0].artist, "Artist")
        self.assertEqual(albums[1].artist, None)

    def test_rejects_duplicate_album_reference(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            library.create_album(
                Album(title="Album", artist="Artist", genre="Pop", tracks=())
            )

            with self.assertRaisesRegex(LibraryError, "already exists"):
                library.create_album(
                    Album(title="Album", artist="Other Artist", genre="Pop", tracks=())
                )

    def test_creates_complete_album_from_model(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            album = Album(
                title="Imported Album",
                artist="Artist",
                composer="Composer",
                genre="Classical",
                url="https://example.com/recording",
                tracks=(
                    AlbumTrack(
                        title="Opening",
                        start_ms=1_000,
                        end_ms=5_000,
                        chapters=(Chapter(1_000, "Intro"),),
                    ),
                ),
            )

            reference = library.create_album(album)
            loaded = library.load_album(reference)

        self.assertEqual(reference, "imported-album")
        self.assertEqual(loaded.title, "Imported Album")
        self.assertEqual(loaded.tracks[0].url, None)
        self.assertEqual(loaded.tracks[0].chapters, (Chapter(1_000, "Intro"),))

    def test_overwrite_replaces_existing_album_graph(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            library.create_album(
                Album(title="Album", artist="Artist", genre="Pop", tracks=())
            )
            library.create_track("album", title="Stale Track")

            replacement = Album(
                title="Album",
                artist="New Artist",
                genre="Jazz",
                tracks=(AlbumTrack(title="Fresh Track"),),
            )
            library.create_album(replacement, overwrite=True)
            loaded = library.load_album("album")

        self.assertEqual(loaded.artist, "New Artist")
        self.assertEqual(loaded.genre, "Jazz")
        self.assertEqual([track.title for track in loaded.tracks], ["Fresh Track"])

    def test_failed_overwrite_keeps_existing_album(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            library.create_album(
                Album(title="Album", artist="Artist", genre="Pop", tracks=())
            )
            library.create_track("album", title="Existing Track")

            with self.assertRaisesRegex(ValueError, "title"):
                library.create_album(
                    Album(
                        title="Album",
                        artist="New Artist",
                        genre="Jazz",
                        tracks=(AlbumTrack(title=""),),
                    ),
                    overwrite=True,
                )

            loaded = library.load_album("album")

        self.assertEqual(loaded.artist, "Artist")
        self.assertEqual([track.title for track in loaded.tracks], ["Existing Track"])

    def test_deletes_album_and_cascades_tracks_and_chapters(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            library = Library(root=root, name="Music")
            library.initialize()
            library.create_album(
                Album(title="Album", artist="Artist", genre="Pop", tracks=())
            )
            library.create_track(
                "album",
                title="Track",
                chapters=(Chapter(0, "Opening", 1_000),),
            )
            library.create_track("album", title="Second Track")

            library.delete_album("album")

            self.assertEqual(library.list_albums(), [])
            with sqlite3.connect(library.database_path) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM tracks").fetchone(),
                    (0,),
                )
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM chapters").fetchone(),
                    (0,),
                )
            with self.assertRaisesRegex(LibraryError, "album not found: album"):
                library.load_album("album")

    def test_delete_rejects_unknown_album_reference(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            library = Library(root=root, name="Music")
            library.initialize()

            with self.assertRaisesRegex(LibraryError, "album not found: missing"):
                library.delete_album("missing")

    def test_rejects_blank_genre(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            with self.assertRaisesRegex(ValueError, "genre"):
                library.create_album(
                    Album(title="Album", artist="Artist", genre=" ", tracks=())
                )


if __name__ == "__main__":
    unittest.main()
