# Album Maestro

Album Maestro started from a simple frustration: a long recording may contain a
complete album, but a music library sees only one file. Classical music makes
this especially noticeable—a symphony, sonata, or recital may contain several
movements that listeners expect to find, name, and play separately. Turning
that recording into something you can browse takes more than splitting audio;
album and track identity, credits, references, timing, chapters, and tags all
need to stay together.

Album Maestro is a local Python command-line tool for doing that. You describe
an album built from one or more source recordings, including compilations with
different artists per track. The details live in a searchable SQLite catalog,
where album-level values provide defaults and individual tracks can override
them. When you are ready, Album Maestro uses that catalog to produce tagged
files that ordinary music players can browse. Your source files stay in the
library you choose, and the project is not tied to a particular genre.

## Requirements and install

- Python 3.11 or newer
- [FFmpeg](https://ffmpeg.org/), including `ffmpeg` and `ffprobe` on `PATH`,
  when processing audio

```shell
git clone https://github.com/henry-zhao-dev/album-maestro.git
cd album-maestro
poetry install
poetry run album-maestro --help
```

You can also install the checkout with `python -m pip install .` and use
`album-maestro` directly. Install FFmpeg with `brew install ffmpeg` on macOS or
`sudo apt install ffmpeg` on Debian and Ubuntu.

## Quick start

Start by creating a library:

```shell
album-maestro init ~/Music/album-maestro
```

This creates:

```text
~/Music/album-maestro/
├── album-maestro.db
└── sources/
```

Put permitted source files in `sources/`, then create and edit an album:

```shell
album-maestro create --library ~/Music/album-maestro
album-maestro edit ALBUM --library ~/Music/album-maestro
album-maestro process ALBUM --library ~/Music/album-maestro
```

`create` asks for the album details and starts with an empty album. Use `edit`
to add, change, or remove tracks. Enter source paths as bare filenames such as
`recording.m4a`; they must already exist in the library's `sources/` directory.

Every command that works with a library accepts `--library DIRECTORY` and
defaults to the current directory. Commands are at the root, so use
`album-maestro create`, not `album-maestro album create`.

## Commands

| Command | Purpose |
| --- | --- |
| `init [DIRECTORY]` | Create a library; `--name` sets its name |
| `create` | Create an album interactively |
| `list` | List albums and track counts |
| `search` | Search title, artist, composer, and genre |
| `show ALBUM` | Show album details and tracks |
| `edit ALBUM` | Edit album metadata and tracks interactively |
| `delete ALBUM` | Remove an album, tracks, and chapters from SQLite |
| `process ALBUM...` / `process --all` | Create tagged files from local sources; `--output` changes the destination |
| `import --json FILE` / `import --directory DIRECTORY` | Validate JSON and write albums to SQLite |
| `export ALBUM...` / `export --all` | Write SQLite albums as JSON |

Run `album-maestro COMMAND --help` for the full options. Search filters are
case-insensitive and can be combined.

## Catalog and JSON specifications

SQLite is the working catalog and the single source of truth. JSON gives you a
portable way to author or move album specifications; it is not a second catalog
to keep synchronized.

An imported album needs a title, genre, and at least one track. Album and track
fields cover `artist`, `composer`, `genre`, reference `url`, local
`file_source`, track timestamps, and chapters. Track values override album
defaults; an album without an artist uses `Various Artists` in output metadata.
Each track needs a URL or local source unless the album provides one. Local
sources must already exist inside `sources/`; paths that escape the directory
are rejected. Chapters can be imported and processed, but are not yet edited
by the interactive prompt.

Import one file or a directory of JSON files:

```shell
album-maestro import --json album.json --library ~/Music/album-maestro
album-maestro import --directory albums --library ~/Music/album-maestro
```

Existing album references are rejected unless `--overwrite` is passed. A
directory import continues after individual failures and returns a failure
status if any file could not be imported.

Export one album or all albums:

```shell
album-maestro export ALBUM --json album.json \
  --library ~/Music/album-maestro
album-maestro export --all --directory albums \
  --library ~/Music/album-maestro
```

Directory exports use `<album-reference>.json`. Existing files are not replaced
unless `--overwrite` is passed, and exports preserve defaults, overrides,
timestamps, and chapters.

## Processing local audio

Once an album has sources, `process` uses a track's `file_source`, falling back
to the album source. It checks duration with `ffprobe`, optionally trims the
source, applies standard `title`, `artist`, `album_artist`, `album`, `composer`,
`genre`, and `track` tags, adds chapters, and writes the result. Embedded
artwork is retained when present.

The default output layout is:

```text
tracks/<album artist>/<album title>/<track title><source extension>
```

Processing continues after track errors and returns a failure status if any
track failed. URLs are never used as audio sources. Deleting an album removes
catalog records only; source and generated audio files remain.

## How it works

The command handlers call the library layer, which validates inputs and writes
relational data with raw SQLite queries. The `specs/` package handles JSON
schema and timestamps. For processing, album defaults become a resolved track
request, then `pipeline.py` and `audio.py` run the FFmpeg/ffprobe steps.

## Examples and development

[`examples/README.md`](examples/README.md) shows how to import the example
albums and optionally obtain their Wikimedia Commons source audio. Use only
media you have permission to use; attribution details are in
[`examples/sources/ATTRIBUTION.md`](examples/sources/ATTRIBUTION.md).

Run the tests with:

```shell
poetry run pytest
```

Album Maestro is licensed under the [MIT License](LICENSE). `jsonschema` is a
runtime dependency; FFmpeg and ffprobe are separate system requirements.
