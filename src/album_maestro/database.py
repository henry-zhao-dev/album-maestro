"""SQLite storage for the Album Maestro catalog."""

import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any

from album_maestro.models import Album, AlbumSummary, AlbumTrack, Chapter


class DatabaseError(ValueError):
    """Raised when the Album Maestro database cannot be opened or changed."""


SCHEMA = """
-- This table stores the database's single library record
CREATE TABLE IF NOT EXISTS library (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL
);

-- Each row represents an album
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY,
    reference TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    artist TEXT,
    composer TEXT,
    genre TEXT NOT NULL,
    url TEXT
);

-- Each row represents a track inside an existing album
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY,
    -- Delete associated tracks automatically when their album is deleted
    album_id INTEGER NOT NULL REFERENCES albums(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    artist TEXT,
    composer TEXT,
    genre TEXT,
    url TEXT,
    start_ms INTEGER,
    end_ms INTEGER,
    -- Each album can have only one track at a given position
    UNIQUE (album_id, position)
);

-- Each row represents a chapter inside an existing track
CREATE TABLE IF NOT EXISTS chapters (
    id INTEGER PRIMARY KEY,
    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    title TEXT,
    start_ms INTEGER NOT NULL,
    end_ms INTEGER,
    UNIQUE (track_id, position)
);

CREATE INDEX IF NOT EXISTS albums_artist_idx ON albums (artist);
CREATE INDEX IF NOT EXISTS albums_composer_idx ON albums (composer);
CREATE INDEX IF NOT EXISTS albums_genre_idx ON albums (genre);
"""


def initialize(path: str | Path, name: str) -> Path:
    """Create and initialize a new Album Maestro database."""

    database_path = Path(path)
    if database_path.exists():
        raise DatabaseError(f"{database_path} already exists")

    try:
        with sqlite3.connect(database_path) as connection:
            _configure(connection)
            connection.executescript(SCHEMA)
            connection.execute("INSERT INTO library (id, name) VALUES (1, ?)", (name,))
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error
    return database_path


def load_name(path: str | Path) -> str:
    """Read the library name from an initialized database."""

    try:
        with sqlite3.connect(path) as connection:
            _ensure_schema(connection)
            row = connection.execute("SELECT name FROM library WHERE id = 1").fetchone()
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error
    if row is None:
        raise DatabaseError("database does not contain an Album Maestro library")
    return row[0]


def create_album(
    path: str | Path,
    *,
    reference: str,
    title: str,
    artist: str | None,
    composer: str | None,
    genre: str,
    url: str | None,
) -> AlbumSummary:
    """Insert an album and return its summary."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            cursor = connection.execute(
                """
                INSERT INTO albums (reference, title, artist, composer, genre, url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (reference, title, artist, composer, genre, url),
            )
            album_id = cursor.lastrowid
            if album_id is None:
                raise DatabaseError("failed to obtain the new album ID")
    except sqlite3.IntegrityError as error:
        if "albums.reference" in str(error):
            raise DatabaseError(f"album already exists: {reference}") from error
        raise DatabaseError(str(error)) from error
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error

    return AlbumSummary(
        id=album_id,
        reference=reference,
        title=title,
        artist=artist,
        composer=composer,
        genre=genre,
        track_count=0,
    )


def list_albums(path: str | Path) -> list[AlbumSummary]:
    """Return all album summaries in title order."""

    return _album_summary_rows(path)


def search_albums(
    path: str | Path,
    *,
    title: str | None = None,
    artist: str | None = None,
    composer: str | None = None,
    genre: str | None = None,
) -> list[AlbumSummary]:
    """Search album text fields using case-insensitive substring matching."""

    filters: list[str] = []
    parameters: list[str] = []
    for column, value in (
        ("title", title),
        ("artist", artist),
        ("composer", composer),
        ("genre", genre),
    ):
        if value:
            filters.append(f"albums.{column} LIKE ? COLLATE NOCASE")
            parameters.append(f"%{value}%")

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    return _album_summary_rows(path, where=where, parameters=parameters)


def get_album(path: str | Path, reference: str) -> Album:
    """Load one complete album and its tracks from SQLite."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            album_row = connection.execute(
                """
                SELECT id, title, artist, composer, genre, url
                FROM albums
                WHERE reference = ?
                """,
                (reference,),
            ).fetchone()
            if album_row is None:
                raise DatabaseError(f"album not found: {reference}")

            track_rows = connection.execute(
                """
                SELECT id, title, artist, composer, genre, url, start_ms, end_ms
                FROM tracks
                WHERE album_id = ?
                ORDER BY position
                """,
                (album_row[0],),
            ).fetchall()
            tracks = [
                _track_from_row(connection, track_row) for track_row in track_rows
            ]
    except DatabaseError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error

    return Album(
        title=album_row[1],
        artist=album_row[2],
        composer=album_row[3],
        genre=album_row[4],
        url=album_row[5],
        tracks=tuple(tracks),
    )


def update_album(path: str | Path, reference: str, **fields: Any) -> None:
    """Update editable album fields by reference."""

    _update_row(path, "albums", "reference", reference, fields, {
        "title", "artist", "composer", "genre", "url"
    })


def create_track(
    path: str | Path,
    reference: str,
    *,
    title: str,
    artist: str | None,
    composer: str | None,
    genre: str | None,
    url: str | None,
    start_ms: int | None,
    end_ms: int | None,
    chapters: tuple[Chapter, ...] = (),
) -> int:
    """Append one track to an album and return its position."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            album_id = _album_id(connection, reference)
            position = connection.execute(
                "SELECT COALESCE(MAX(position), 0) + 1 FROM tracks WHERE album_id = ?",
                (album_id,),
            ).fetchone()[0]
            track_id = connection.execute(
                """
                INSERT INTO tracks (
                    album_id, position, title, artist, composer, genre, url,
                    start_ms, end_ms
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    album_id,
                    position,
                    title,
                    artist,
                    composer,
                    genre,
                    url,
                    start_ms,
                    end_ms,
                ),
            ).lastrowid
            if track_id is None:
                raise DatabaseError("failed to obtain the new track ID")
            _insert_chapters(connection, track_id, chapters)
    except DatabaseError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error
    return position


def update_track(path: str | Path, reference: str, position: int, **fields: Any) -> None:
    """Update one track's editable fields."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            track_id = _track_id(connection, reference, position)
            _update_row_by_id(
                connection,
                "tracks",
                track_id,
                fields,
                {"title", "artist", "composer", "genre", "url", "start_ms", "end_ms"},
            )
    except DatabaseError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error


def delete_track(path: str | Path, reference: str, position: int) -> None:
    """Delete one track and close the position gap."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            album_id = _album_id(connection, reference)
            track_id = _track_id(connection, reference, position)
            connection.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
            connection.execute(
                """
                UPDATE tracks
                SET position = position - 1
                WHERE album_id = ? AND position > ?
                """,
                (album_id, position),
            )
    except DatabaseError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error


def reference_from_text(value: str, *, label: str) -> str:
    """Convert display text to a canonical filename-like reference."""

    normalized = re.sub(r"['’ʼ]", "", unicodedata.normalize("NFKD", value))
    normalized = normalized.encode("ascii", "ignore").decode()
    reference = re.sub(r"[^a-z0-9]+", "-", normalized.casefold()).strip("-")
    if not reference:
        raise DatabaseError(f"{label} cannot form a catalog reference")
    return reference


def _configure(connection: sqlite3.Connection) -> None:
    """Apply connection-level SQLite settings."""

    connection.execute("PRAGMA foreign_keys = ON")


def _ensure_schema(connection: sqlite3.Connection) -> None:
    """Apply additive schema changes to an existing database."""

    connection.executescript(SCHEMA)


def _album_summary_rows(
    path: str | Path,
    *,
    where: str = "",
    parameters: list[str] | None = None,
) -> list[AlbumSummary]:
    """Run the shared album summary query."""

    try:
        with sqlite3.connect(path) as connection:
            rows = connection.execute(
                f"""
                SELECT
                    albums.id,
                    albums.reference,
                    albums.title,
                    albums.artist,
                    albums.composer,
                    albums.genre,
                    COUNT(tracks.id) AS track_count
                FROM albums
                LEFT JOIN tracks ON tracks.album_id = albums.id
                {where}
                GROUP BY albums.id
                ORDER BY albums.title COLLATE NOCASE, albums.id
                """,
                parameters or [],
            ).fetchall()
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error
    return [AlbumSummary(*row) for row in rows]


def _album_id(connection: sqlite3.Connection, reference: str) -> int:
    """Resolve an album reference to its primary key."""

    row = connection.execute(
        "SELECT id FROM albums WHERE reference = ?", (reference,)
    ).fetchone()
    if row is None:
        raise DatabaseError(f"album not found: {reference}")
    return row[0]


def _track_id(
    connection: sqlite3.Connection, reference: str, position: int
) -> int:
    """Resolve an album track position to its primary key."""

    row = connection.execute(
        """
        SELECT tracks.id
        FROM tracks
        JOIN albums ON albums.id = tracks.album_id
        WHERE albums.reference = ? AND tracks.position = ?
        """,
        (reference, position),
    ).fetchone()
    if row is None:
        raise DatabaseError(f"track {position} not found in album: {reference}")
    return row[0]


def _track_from_row(
    connection: sqlite3.Connection, row: tuple[Any, ...]
) -> AlbumTrack:
    """Convert one track row and its chapters into a domain model."""

    chapter_rows = connection.execute(
        """
        SELECT title, start_ms, end_ms
        FROM chapters
        WHERE track_id = ?
        ORDER BY position
        """,
        (row[0],),
    ).fetchall()
    return AlbumTrack(
        title=row[1],
        artist=row[2],
        composer=row[3],
        genre=row[4],
        url=row[5],
        start_ms=row[6],
        end_ms=row[7],
        chapters=tuple(Chapter(start_ms=chapter[1], title=chapter[0], end_ms=chapter[2]) for chapter in chapter_rows),
    )


def _insert_chapters(
    connection: sqlite3.Connection, track_id: int, chapters: tuple[Chapter, ...]
) -> None:
    """Insert chapter markers for a newly created track."""

    connection.executemany(
        """
        INSERT INTO chapters (track_id, position, title, start_ms, end_ms)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            (track_id, position, chapter.title, chapter.start_ms, chapter.end_ms)
            for position, chapter in enumerate(chapters, start=1)
        ],
    )


def _update_row(
    path: str | Path,
    table: str,
    key_column: str,
    key_value: str,
    fields: dict[str, Any],
    allowed: set[str],
) -> None:
    """Update a whitelisted set of columns by a text key."""

    try:
        with sqlite3.connect(path) as connection:
            _configure(connection)
            row = connection.execute(
                f"SELECT id FROM {table} WHERE {key_column} = ?", (key_value,)
            ).fetchone()
            if row is None:
                raise DatabaseError(f"album not found: {key_value}")
            _update_row_by_id(connection, table, row[0], fields, allowed)
    except DatabaseError:
        raise
    except (OSError, sqlite3.Error) as error:
        raise DatabaseError(str(error)) from error


def _update_row_by_id(
    connection: sqlite3.Connection,
    table: str,
    row_id: int,
    fields: dict[str, Any],
    allowed: set[str],
) -> None:
    """Update a whitelisted set of columns by primary key."""

    invalid = set(fields) - allowed
    if invalid:
        raise DatabaseError(f"unsupported fields: {', '.join(sorted(invalid))}")
    if not fields:
        return
    assignments = ", ".join(f"{column} = ?" for column in fields)
    values = [*fields.values(), row_id]
    connection.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", values)
