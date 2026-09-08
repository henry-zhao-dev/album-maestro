# Album Maestro

Album Maestro is a Python CLI for turning long-form recordings into albums you
can actually keep and play. It lets you organize albums, tracks, metadata, and
chapter boundaries in a local SQLite database, then export the catalog as
portable JSON specifications.

The goal is not to build another streaming service or music player. It is a
free, open-source album authoring and catalog management tool: describe how a
permitted media source should become an album, and keep the resulting
specification under your control.

The code keeps catalog rules, library operations, CLI interaction,
specification import/export, and audio processing separate so each area can
evolve without forcing changes elsewhere. Besides making the current behavior
easier to test, this gives future interfaces, such as a GUI, a way to reuse the
same core logic.

## Engineering highlights

- SQLite constraints and readable library-level validation errors
- A local SQLite catalog with relational album and track data
- Resolved track metadata, time ranges, and chapter boundaries
- Metadata and chapter embedding through FFmpeg and ffprobe subprocesses
- Interactive CLI workflows with explicit overwrite and partial-failure
  handling
- Automated tests across the CLI, specifications, library operations,
  prompts, and audio pipeline

## Architecture

| Area | Responsibility |
| --- | --- |
| [`commands/`](src/album_maestro/commands/) | CLI argument handling, prompts, and user-facing output |
| [`database.py`](src/album_maestro/database.py) | SQLite schema and catalog persistence |
| [`library.py`](src/album_maestro/library.py) | Library-level operations shared independently of the CLI |
| [`models.py`](src/album_maestro/models.py) | Resolved album, track, and chapter models |
| [`audio.py`](src/album_maestro/audio.py) | Audio inspection and editing through FFmpeg and ffprobe |
| [`pipeline.py`](src/album_maestro/pipeline.py) | Source-audio track processing and metadata orchestration |

## Project status and responsible use

Album Maestro is an early-stage CLI rather than a production service. Album
and track editing is being built incrementally through the CLI. The project is
not affiliated with or endorsed by any media platform or FFmpeg.

This repository does not include media files and its example reference URLs are
placeholders. Album Maestro does not grant rights to third-party content or
override the terms of any platform. You are responsible for the source
references and media you provide, and for complying with applicable laws,
content licenses, and platform terms.

## Requirements

- Python 3.11 or newer
- [FFmpeg](https://ffmpeg.org/), including `ffmpeg` and `ffprobe` on `PATH`,
  when using the audio-processing helpers

For example, install FFmpeg with Homebrew on macOS or apt on Debian/Ubuntu:

```shell
brew install ffmpeg
# or: sudo apt install ffmpeg
```

## Install

From a source checkout, install the project with Poetry:

```shell
git clone https://github.com/henry-zhao-dev/album-maestro.git
cd album-maestro
poetry install
```

You can also install the package with pip from the checkout:

```shell
python -m pip install .
```

Verify the installation:

```shell
poetry run album-maestro --help
```

If you installed with pip, use `album-maestro` directly. If you installed with
Poetry, prefix commands with `poetry run` unless the Poetry environment is
activated.

## Quick start

Create a library in a directory of your choice:

```shell
album-maestro init ~/Music/album-maestro
```

The library name defaults to the directory name. Set it explicitly with
`--name` when needed:

```shell
album-maestro init ~/Music/album-maestro --name "My Music Library"
```

The command creates this layout:

```text
~/Music/album-maestro/
├── album-maestro.db
└── sources/
```

Create an album draft interactively:

```shell
album-maestro create --library ~/Music/album-maestro
```

The command asks for the title, optional album artist, optional composer,
genre, optional reference URL, and optional local file source. Leave the album
artist blank for a compilation whose tracks have different artists. Local file
sources are stored as paths relative to the library, such as
`recording.m4a`; Album Maestro stores it as `sources/recording.m4a`.

List the catalog with:

```shell
album-maestro list --library ~/Music/album-maestro
```

## SQLite catalog

Album Maestro stores the catalog in `album-maestro.db`. The database is the
single source of truth for album and track metadata; there is no JSON catalog
to edit or keep synchronized.

Create an album through the CLI:

```shell
album-maestro create --library ~/Music/album-maestro
```

The album fields are plain text:

- `artist` is the default artist and the value used for the output
  `album_artist` tag.
- `composer` is an independent optional credit.
- `genre` is explicit and required.
- `url` is the default reference URL.
- `file_source` is the default local audio filename stored under `sources/`.

Track-level artist, composer, genre, reference URL, local file source, timestamps, and
chapters are managed through the database-backed editing workflow. JSON uses `url`
for the reference URL and `file_source` for the local audio path. A track’s local
file source overrides the album-level default when provided.

List the catalog:

```shell
album-maestro list --library ~/Music/album-maestro
```

The list command queries SQLite and displays each album’s reference, title,
artist, genre, and current track count.

Import an album specification into SQLite:

```shell
album-maestro import --json albums/beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro
```

Import every JSON file directly inside a directory:

```shell
album-maestro import --directory albums \
  --library ~/Music/album-maestro
```

Import validates each file against the packaged album schema. By default,
existing album references are rejected. Pass `--overwrite` to replace an
existing album, including all of its tracks and chapters.

Export one album back to a JSON specification:

```shell
album-maestro export beethoven-symphony-no-5 \
  --json beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro
```

Export every album to one file per album:

```shell
album-maestro export --all --directory albums \
  --library ~/Music/album-maestro
```

Export preserves album-level defaults and track-level overrides so the JSON
can be edited and imported again. Existing output files are not replaced
unless `--overwrite` is passed.

## Album workflow

Inspect the catalog and one album with:

```shell
album-maestro list --library ~/Music/album-maestro
album-maestro search --artist Beethoven --library ~/Music/album-maestro
album-maestro show beethoven-symphony-no-5 \
  --library ~/Music/album-maestro
```

Edit album metadata and manage tracks interactively:

```shell
album-maestro edit beethoven-symphony-no-5 \
  --library ~/Music/album-maestro
```

Delete an album from the catalog:

```shell
album-maestro delete beethoven-symphony-no-5 \
  --library ~/Music/album-maestro
```

This removes the album, its tracks, and chapters from SQLite.

## Troubleshooting

### `external command not found: ffmpeg` or `ffprobe`

Install FFmpeg and ensure both commands are available on `PATH`:

```shell
ffmpeg -version
ffprobe -version
```

### Existing files are not replaced

This is the default safety behavior. Use `--overwrite` when you intentionally
want to replace existing output files.

## Current limitations

- Album and track editing is interactive; batch editing is future work.
- Audio processing is exposed through reusable helpers and may be expanded in
  future CLI workflows.

## Third-party software

Album Maestro is licensed under the [MIT License](LICENSE).

Album Maestro uses
[jsonschema](https://github.com/python-jsonschema/jsonschema), which is licensed
under the [MIT License](https://github.com/python-jsonschema/jsonschema/blob/main/COPYING).

FFmpeg and ffprobe are external system requirements and are not distributed
with Album Maestro. FFmpeg is generally licensed under LGPL-2.1-or-later, while
the license of a particular build may differ based on its enabled components;
see [FFmpeg's legal information](https://ffmpeg.org/legal.html).

## Development

Run the test suite from the project checkout:

```shell
poetry run pytest
```
