# Album Maestro

Album Maestro is a Python CLI for turning long-form recordings into albums you
can actually keep and play. Classical recordings are often available on
YouTube as one long video rather than as a properly structured release. Album
Maestro lets you describe the album, tracks, metadata, and chapter boundaries
in reproducible JSON, then downloads and produces tagged audio files that work
with established players such as Apple Music, VLC, and Windows Media Player.

The goal is not to build another streaming service or music player. It is a
free, open-source album authoring and processing tool: use any permitted media
source, decide how it should become an album, and keep the resulting files and
specification under your control.

The code keeps catalog rules, library operations, CLI interaction,
downloading, and audio processing separate so each area can evolve without
forcing changes elsewhere. Besides making the current behavior easier to
test, this gives future interfaces, such as a GUI, a way to reuse the same
core logic.

## Engineering highlights

- JSON Schema validation with readable, location-aware configuration errors
- Self-contained album specifications with inherited defaults and overrides
- Shared-source processing that downloads a recording once and creates
  multiple trimmed tracks from it
- Metadata and chapter embedding through FFmpeg and ffprobe subprocesses
- Interactive CLI workflows with explicit overwrite and partial-failure
  handling
- Automated tests across the CLI, specifications, library operations,
  downloader behavior, prompts, and audio pipeline

## Architecture

| Area | Responsibility |
| --- | --- |
| [`commands/`](src/album_maestro/commands/) | CLI argument handling, prompts, and user-facing output |
| [`specs/`](src/album_maestro/specs/) | JSON loading, parsing, schema validation, and catalog storage |
| [`library.py`](src/album_maestro/library.py) | Library-level operations shared independently of the CLI |
| [`models.py`](src/album_maestro/models.py) | Resolved album, track, and chapter models |
| [`downloader.py`](src/album_maestro/downloader.py) | Source acquisition through the yt-dlp Python API |
| [`audio.py`](src/album_maestro/audio.py) | Audio inspection and editing through FFmpeg and ffprobe |
| [`pipeline.py`](src/album_maestro/pipeline.py) | Album download and track-creation orchestration |

## Project status and responsible use

Album Maestro is an early-stage CLI rather than a production service. Album
tracks are currently authored by editing JSON; a guided editor and GUI are
possible future work. The project is not affiliated with or endorsed by
YouTube, yt-dlp, or FFmpeg.

This repository does not include downloaded media and its example URLs are
placeholders. Album Maestro does not grant rights to third-party content or
override the terms of any platform. Only download or process media when you
have permission and when doing so complies with applicable laws, content
licenses, and platform terms. You are responsible for the URLs and media you
provide.

## Requirements

- Python 3.11 or newer
- [FFmpeg](https://ffmpeg.org/), including `ffmpeg` and `ffprobe` on `PATH`
- Network access to the YouTube URLs in your album files

Album Maestro uses `yt-dlp` for downloads and FFmpeg for audio inspection,
trimming, metadata, and chapter tags. If either `ffmpeg` or `ffprobe` is not
available, downloads that need audio processing will fail with an explanatory
error.

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
├── album-maestro.json
├── albums/
└── downloads/
```

Create an album draft interactively:

```shell
album-maestro album create --library ~/Music/album-maestro
```

The command asks for the title, optional album artist, optional composer,
genre, and optional shared URL. Leave the album artist blank for a compilation
whose tracks have different artists. It creates an album JSON file with an
empty `tracks` array. Edit that file to add tracks before downloading.

## Example configurations

The [`examples/`](examples/) directory contains album JSON templates.
The URLs in those files are placeholders and must be replaced with real
YouTube URLs before downloading.

To use the examples:

```shell
album-maestro init ~/Music/album-maestro-example
cp examples/albums/*.json ~/Music/album-maestro-example/albums/
```

After replacing the placeholder URLs, download one album or the entire library:

```shell
album-maestro album download beethoven-symphony-no-5 \
  --library ~/Music/album-maestro-example
album-maestro album download --all --library ~/Music/album-maestro-example
```

## Album files

An album file requires `title`, `genre`, and at least one track. Album metadata
is plain text and self-contained; there are no artist or composer catalog files
to keep synchronized. The album-level `artist` is optional and is the default
artist for its tracks. Use `null` for a compilation whose tracks provide their
own artists. `composer` is an optional plain-text credit:

```json
{
  "title": "Symphony No. 5",
  "artist": "Ludwig van Beethoven",
  "composer": "Ludwig van Beethoven",
  "genre": "Classical",
  "tracks": [
    {
      "title": "I. Allegro con brio",
      "url": "https://youtu.be/replace-with-recording"
    }
  ]
}
```

### Artist, album artist, and composer

Album Maestro maps these fields to standard audio metadata:

- Album `artist` is the default track artist and becomes the output
  `album_artist` tag.
- Track `artist` overrides the album default. If neither is provided, both
  output artist fields use `Various Artists`.
- Album `composer` is an independent optional credit for who wrote the music.
  Track `composer` overrides it. Composer never fills in for a missing artist.
- Album `genre` is explicit and required. Track `genre` overrides it. Genre is
  never inferred from an artist or composer.
- Album `url` is the default source URL. Track `url` overrides it. Without an
  album URL, every track must provide its own URL.

This keeps the common classical cases clear. A recording performed by Hilary
Hahn can have `artist: Hilary Hahn` and `composer: Johann Sebastian Bach`,
while a composer-focused collection can leave the album artist blank and let
the output use `Various Artists`. For pop music, the same fields work in the
usual way: the performer is the artist, the composer is optional, and the
genre is explicit.

For example, a composer-centric album can use:

```json
{
  "title": "Bach: Cello Suites",
  "artist": null,
  "composer": "Johann Sebastian Bach",
  "genre": "Classical",
  "tracks": [
    {
      "title": "Suite No. 1: I. Prelude",
      "url": "https://youtu.be/replace-with-recording"
    }
  ]
}
```

This produces `artist = Various Artists`,
`album_artist = Various Artists`, and
`composer = Johann Sebastian Bach` in the audio file. The composer remains a
separate credit instead of being treated as the performer.

### Shared source recording

Use an album-level `url` when several tracks come from one recording. `start`
and `end` are optional timestamps and accept seconds, `mm:ss`, or `hh:mm:ss`:

```json
{
  "title": "Symphony No. 5",
  "artist": "Frankfurt Radio Symphony Orchestra",
  "composer": "Ludwig van Beethoven",
  "genre": "Classical",
  "url": "https://youtu.be/replace-with-full-recording",
  "tracks": [
    {
      "title": "I. Allegro con brio",
      "start": "0:04",
      "end": "8:20"
    },
    {
      "title": "II. Andante con moto",
      "start": "8:30",
      "end": "19:15"
    }
  ]
}
```

When an album does not have a shared URL, every track must provide its own
`url`. A track may provide an `artist` value to override the album artist.
For a compilation, leave the album artist as `null`:

```json
{
  "title": "Classical Favorites",
  "artist": null,
  "genre": "Classical",
  "tracks": [
    {
      "title": "Symphony No. 5",
      "artist": "Ludwig van Beethoven",
      "url": "https://youtu.be/replace-with-beethoven-recording"
    },
    {
      "title": "Eine kleine Nachtmusik",
      "artist": "Wolfgang Amadeus Mozart",
      "url": "https://youtu.be/replace-with-mozart-recording"
    }
  ]
}
```

Tracks may include chapter markers. Each chapter requires a `start` timestamp;
the title is optional and defaults to `Chapter 1`, `Chapter 2`, and so on:

```json
{
  "title": "Movement",
  "url": "https://youtu.be/replace-with-recording",
  "chapters": [
    {"start": "0:00", "title": "Introduction"},
    {"start": "1:30", "title": "Main theme"}
  ]
}
```

JSON is validated when an album is loaded. The schema rejects unknown fields,
invalid references, missing required values, and malformed timestamps. An album
draft created by `album create` intentionally has no tracks yet, so it must be
edited before it can be downloaded.

## Download albums

Download one album by its reference (the album filename without `.json`):

```shell
album-maestro album download beethoven-symphony-no-5 \
  --library ~/Music/album-maestro
```

Download several albums by passing multiple references, or download every album
with `--all`:

```shell
album-maestro album download beethoven-symphony-no-5 classical-favorites \
  --library ~/Music/album-maestro
album-maestro album download --all --library ~/Music/album-maestro
```

Without `--overwrite`, existing track files are listed and Album Maestro asks
once whether to overwrite them. Answering no skips existing tracks and
continues with tracks that are not present. Pass `--overwrite` to overwrite
existing tracks without prompting.

Generated files are organized as:

```text
downloads/<album artist>/<album title>/<track title>.m4a
```

## Troubleshooting

### `external command not found: ffmpeg` or `ffprobe`

Install FFmpeg and ensure both commands are available on `PATH`:

```shell
ffmpeg -version
ffprobe -version
```

### Album validation errors

Check the filename references and JSON fields against the examples and schemas
in [`src/album_maestro/schemas/`](src/album_maestro/schemas/). The most common issue
is forgetting to add a `tracks` entry or a track `url` when no album-level URL
is present.

### Existing files are not replaced

This is the default safety behavior. Use `--overwrite` when you intentionally
want to replace existing output files.

## Current limitations

- Track editing requires manual JSON changes.
- There is not yet a dedicated `album validate`, `list`, or `show` command.
- Downloads depend on the current behavior and availability of YouTube and
  `yt-dlp`.

## Third-party software

Album Maestro is licensed under the [MIT License](LICENSE).

Album Maestro uses [yt-dlp](https://github.com/yt-dlp/yt-dlp), which is licensed
under the [Unlicense](https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE),
and [jsonschema](https://github.com/python-jsonschema/jsonschema), which is
licensed under the
[MIT License](https://github.com/python-jsonschema/jsonschema/blob/main/COPYING).

FFmpeg and ffprobe are external system requirements and are not distributed
with Album Maestro. FFmpeg is generally licensed under LGPL-2.1-or-later, while
the license of a particular build may differ based on its enabled components;
see [FFmpeg's legal information](https://ffmpeg.org/legal.html).

## Development

Run the test suite from the project checkout:

```shell
poetry run pytest
```
