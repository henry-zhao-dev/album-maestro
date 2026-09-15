# Album Maestro

The project began with a simple frustration: a long recording may contain a
complete album, but a music library sees only one file. As a classical music
enthusiast, I find this especially noticeable. A symphony, sonata, or recital
may contain several movements that listeners expect to find, name, and play
separately.

Album Maestro turns those recordings into player-friendly albums. You provide
the album and track details—even for multi-movement recordings or compilations
with different artists—and it creates separate, tagged files that ordinary
music players can browse. It works with local audio files and is not tied to a
particular genre.

## Requirements and installation

Docker is the primary way to run Album Maestro. The project image supplies
Python, Poetry, Album Maestro, FFmpeg, and `ffprobe` together.

### Docker setup

From the repository checkout, build the image and verify the CLI:

```shell
docker build --tag album-maestro:local .
./scripts/install-docker-cli
export PATH="$HOME/.local/bin:$PATH"
album-maestro --help
```

The installer places a small Docker launcher in `~/.local/bin`. If that
directory is not already on `PATH`, add the exported line to your shell
profile. The launcher mounts `~/Music/album-maestro` by default; set
`ALBUM_MAESTRO_LIB` to mount another host directory.

The complete workflow covers library initialization, source audio, interactive
commands, batch processing, ownership, and volumes in
[`docs/quick-start.md`](docs/quick-start.md).

### Manual installation fallback

If Docker is unavailable, install the runtime dependencies directly:

- Python 3.11 or newer
- [Poetry](https://python-poetry.org/)
- [FFmpeg](https://ffmpeg.org/), including `ffmpeg` and `ffprobe` on `PATH`

```shell
git clone https://github.com/henry-zhao-dev/album-maestro.git
cd album-maestro
poetry install
eval $(poetry env activate)
album-maestro --help
```

Install FFmpeg with `brew install ffmpeg` on macOS or `sudo apt install ffmpeg`
on Debian and Ubuntu.

## See it in action

Album Maestro turns a long local recording into a browsable, tagged album. The
typical workflow is:

```shell
album-maestro create
album-maestro edit the-four-seasons-autumn
album-maestro list
album-maestro process the-four-seasons-autumn
```

After processing, the catalog shows one album with three tracks, and the
player-friendly files are written under `tracks/`:

```text
$ album-maestro list
REFERENCE                TITLE                     ARTIST                        GENRE      TRACKS
-----------------------  ------------------------  ----------------------------  ---------  ------
the-four-seasons-autumn  The Four Seasons: Autumn  The Modena Chamber Orchestra  Classical  3

$ album-maestro process the-four-seasons-autumn
[INFO] Processed .../I. Allegro.mp3
[INFO] Processed .../II. Adagio molto.mp3
[INFO] Processed .../III. Allegro.mp3
```

For complete Docker setup, source preparation, interactive prompts, catalog
inspection, and local processing, see the
[quick-start guide](docs/quick-start.md).

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
