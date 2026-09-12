# Album Maestro

The project began with a simple frustration: a long recording may contain a
complete album, but a music library sees only one file. As a classical music
enthusiast, I find this especially noticeable. A symphony, sonata, or recital
may contain several movements that listeners expect to find, name, and play
separately.

Album Maestro is a local Python command-line tool for turning those recordings
into player-friendly albums. You describe an album built from one or more source
recordings, including compilations with different artists per track. The details
live in a searchable SQLite catalog, where album-level values provide defaults
and individual tracks can override them. When you are ready, the tool uses that
catalog to produce tagged files that ordinary music players can browse. Source
files remain in the library you choose, and the project is not tied to a
particular genre.

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

Alternatively, install the project from the repository with
`python -m pip install .` and use the `album-maestro` command directly. Install
FFmpeg with `brew install ffmpeg` on macOS or `sudo apt install ffmpeg` on
Debian and Ubuntu.

## Quick start

A library is the directory created by `init`. It contains the catalog and the
local audio files used for processing:

- `album-maestro.db` is the SQLite database that stores the library catalog.
- `sources/` is the directory for local audio files. A `file_source` points to
  a file in this directory.

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

Put permitted source files in `sources/`, then change into the library
directory. The commands below use the current directory as their library:

```shell
cd ~/Music/album-maestro
album-maestro create
album-maestro edit ALBUM
album-maestro process ALBUM
```

For a complete interactive walkthrough, see
[`docs/quick-start.md`](docs/quick-start.md). It uses a single source recording
and the three movement ranges defined in
[`examples/albums/vivaldi-autumn.json`](examples/albums/vivaldi-autumn.json).
The guide includes representative prompts and output.

After processing the album, `album-maestro list` gives a compact summary of its
entry in the SQLite catalog:

```text
$ album-maestro list
REFERENCE                TITLE                     ARTIST                        GENRE      TRACKS
-----------------------  ------------------------  ----------------------------  ---------  ------
the-four-seasons-autumn  The Four Seasons: Autumn  The Modena Chamber Orchestra  Classical  3
```

To inspect the details behind that row, run `album-maestro show ALBUM`. The command
prints the album metadata and its tracks, including source timing.

```text
$ album-maestro show the-four-seasons-autumn
Title:          The Four Seasons: Autumn
Artist:         The Modena Chamber Orchestra
Album artist:   The Modena Chamber Orchestra
Composer:       Antonio Vivaldi
Genre:          Classical

Reference URL:  https://musopen.org/music/14910-the-four-seasons-op-8/
File source:    vivaldi-autumn.mp3

TRACKS
  #  TITLE                START    END
  1  I. Allegro           0:00     5:29
  2  II. Adagio molto     5:29     8:50
  3  III. Allegro         8:50     12:13
```

Library commands use the current directory by default. If you run one from
elsewhere, pass `--library DIRECTORY`, for example:

```shell
album-maestro list --library ~/Music/album-maestro
```

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

You can create and edit albums through the CLI, but you can also keep an album
specification in a JSON file if that suits your workflow. Import it with
`album-maestro import --json FILE`. JSON is readable and portable: you can copy
it anywhere, review or edit it by hand, or use an LLM to help put one together.

Once imported, the album lives in SQLite. That database is the catalog behind
the commands and the single source of truth for album and track metadata. JSON
complements SQLite as the format for creating and moving album definitions,
rather than a second catalog to synchronize. You can also export catalog data
back to JSON.

For field requirements, inherited defaults, source validation, and a complete
workflow, see
[`docs/sync-catalog-with-json.md`](docs/sync-catalog-with-json.md).

## Processing local audio

The `album-maestro process ALBUM` command turns each catalog track into a
player-friendly audio file. Album defaults and track overrides are first
resolved into a complete request containing the source file, time range,
metadata, track number, and optional chapters. The source is resolved inside
the library's `sources/` directory, where missing files and paths that escape
the directory are rejected.

The processing pipeline then:

- uses `ffprobe` to read the source duration and verifies that the selected time
  range fits within the recording;
- uses FFmpeg to trim the requested segment, preserving the first audio stream
  and optional embedded artwork while excluding unrelated data or text streams;
- applies standard `title`, `artist`, `album_artist`, `album`, `composer`,
  `genre`, and `track` tags;
- translates catalog chapters into FFmpeg metadata relative to the trimmed
  output; and
- moves the completed file to a validated path under the selected output
  directory.

Each stage works from a temporary file produced by the previous stage, and the
media operations use stream copying by default, avoiding an unnecessary second
audio encode. The default output layout is:

```text
tracks/<album artist>/<album title>/<track title><source extension>
```

Output path components are checked before writing, so catalog values cannot
escape the output directory. For batch processing, `album-maestro process --all`
or multiple album references logs failures per track and continues with the
remaining work. The command returns a failure status if anything failed, making
progress possible without hiding errors.

URLs are catalog references only and are never used as audio sources. Deleting
an album removes catalog records only; source and generated audio files remain.

## License

Album Maestro is licensed under the [MIT License](LICENSE).
