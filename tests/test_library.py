import sqlite3
import tempfile
import unittest
from pathlib import Path

from album_maestro.library import Library, LibraryError


class InitializeLibraryTests(unittest.TestCase):
    def test_creates_sqlite_library(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir) / "music"
            database_path = Library(root=root, name="My Music").initialize()

            self.assertEqual(database_path, root.resolve() / "album-maestro.db")
            self.assertTrue(database_path.is_file())
            self.assertFalse((root / "albums").exists())
            self.assertTrue((root / "downloads").is_dir())

            with sqlite3.connect(database_path) as connection:
                self.assertEqual(
                    connection.execute("SELECT name FROM library").fetchone(),
                    ("My Music",),
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
        self.assertEqual(music_library.database_path, root.resolve() / "album-maestro.db")
        self.assertEqual(music_library.downloads_dir, root.resolve() / "downloads")

    def test_rejects_incomplete_library_structure(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "album-maestro.db").touch()

            with self.assertRaisesRegex(LibraryError, "library"):
                Library.load(root)

    def test_load_migrates_an_older_database_with_no_chapters_table(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            (root / "downloads").mkdir()
            database_path = root / "album-maestro.db"
            with sqlite3.connect(database_path) as connection:
                connection.executescript(
                    """
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
                    """
                )

            Library.load(root)

            with sqlite3.connect(database_path) as connection:
                self.assertIsNotNone(
                    connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'chapters'"
                    ).fetchone()
                )


class CatalogMutationTests(unittest.TestCase):
    def test_creates_album_in_sqlite(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()

            album = music_library.create_album(
                " Symphony No. 5 ",
                " Ludwig van Beethoven ",
                composer=" Ludwig van Beethoven ",
                genre=" Classical ",
                shared_url=" https://example.com/full ",
            )

        self.assertEqual(album.reference, "symphony-no-5")
        self.assertEqual(album.title, "Symphony No. 5")
        self.assertEqual(album.artist, "Ludwig van Beethoven")
        self.assertEqual(album.composer, "Ludwig van Beethoven")
        self.assertEqual(album.genre, "Classical")
        self.assertEqual(album.track_count, 0)

    def test_lists_albums_in_title_order_with_track_counts(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            root = Path(temporary_dir)
            music_library = Library(root=root, name="Music")
            music_library.initialize()
            music_library.create_album("Zeta", None, genre="Classical")
            music_library.create_album("Alpha", "Artist", genre="Pop")

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
            library.create_album("Album", "Artist", genre="Pop")

            with self.assertRaisesRegex(LibraryError, "already exists"):
                library.create_album("Album", "Other Artist", genre="Pop")

    def test_rejects_blank_genre(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            library = Library(root=Path(temporary_dir), name="Music")
            library.initialize()
            with self.assertRaisesRegex(LibraryError, "genre"):
                library.create_album("Album", "Artist", genre=" ")


if __name__ == "__main__":
    unittest.main()
