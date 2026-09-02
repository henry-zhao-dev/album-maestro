# Album Maestro

Album Maestro is a declarative YouTube audio downloader for classical music. You
describe artists and albums as JSON, then Album Maestro downloads, trims, tags,
and organizes the resulting audio files.

This is an early CLI release. Album tracks are currently authored by editing
JSON directly; a guided editor and GUI are planned for a later release.

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
├── artists/
└── downloads/
```

Create an album draft interactively:

```shell
album-maestro album create --library ~/Music/album-maestro
```

The command asks for the title, artist, optional genre, and optional shared
URL. It creates an album JSON file with an empty `tracks` array. Edit that file
to add tracks before downloading.

## Example configurations

The [`examples/`](examples/) directory contains artist and album JSON templates.
The URLs in those files are placeholders and must be replaced with real
YouTube URLs before downloading.

To use the examples:

```shell
album-maestro init ~/Music/album-maestro-example
cp examples/artists/*.json ~/Music/album-maestro-example/artists/
cp examples/albums/*.json ~/Music/album-maestro-example/albums/
```

After replacing the placeholder URLs, download one album or the entire library:

```shell
album-maestro album download beethoven-symphony-no-5 \
  --library ~/Music/album-maestro-example
album-maestro album download --all --library ~/Music/album-maestro-example
```

## Artist files

An artist file defines reusable metadata. Its filename without `.json` is the
canonical artist reference used by album files:

```text
artists/beethoven.json
```

```json
{
  "name": "Ludwig van Beethoven",
  "default_genre": "Classical"
}
```

The reference is a stable configuration ID, while `name` is the display value
written to audio metadata. `default_genre` is used when an album does not
provide its own genre.

When creating an album, Album Maestro matches the entered artist name against
existing display names without regard to case. If several artists match, it
lists them and asks you to select one. If no artist matches, it creates a new
artist file using the entered name. A genre entered for a new artist becomes
that artist's default genre.

## Album files

An album file requires `title`, `artist`, and at least one track. The album
artist must reference an existing file in `artists/`:

```json
{
  "title": "Symphony No. 5",
  "artist": "beethoven",
  "tracks": [
    {
      "title": "I. Allegro con brio",
      "url": "https://youtu.be/replace-with-recording"
    }
  ]
}
```

For an existing artist, the album genre prompt is prefilled with that artist's
default. The album stores a `genre` only when it differs from the artist's
default; this keeps repeated metadata in the artist file.

### Shared source recording

Use an album-level `url` when several tracks come from one recording. `start`
and `end` are optional timestamps and accept seconds, `mm:ss`, or `hh:mm:ss`:

```json
{
  "title": "Symphony No. 5",
  "artist": "beethoven",
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
`url`. A track may also provide an `artist` reference to override the album
artist, which is useful for compilations:

```json
{
  "title": "Classical Favorites",
  "artist": "various-artists",
  "tracks": [
    {
      "title": "Symphony No. 5",
      "artist": "beethoven",
      "url": "https://youtu.be/replace-with-beethoven-recording"
    },
    {
      "title": "Eine kleine Nachtmusik",
      "artist": "mozart",
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

Without `--overwrite`, existing track files are listed and Album Maestro asks once
whether to overwrite them. Answering no skips existing tracks and continues
with tracks that are not present. Pass `--overwrite` to overwrite existing
tracks without prompting.

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
in [`src/yt_maestro/schemas/`](src/yt_maestro/schemas/). The most common issue
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

## Development

Run the test suite from the project checkout:

```shell
poetry run pytest
```
