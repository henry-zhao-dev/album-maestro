# YT Maestro

Declarative YouTube audio downloader with precision trimming and chaptering, 
tailored for classical music enthusiasts.

## Initialize a music library

Create a library interactively:

```shell
yt-maestro init
```

Pass a directory to create the library there:

```shell
yt-maestro init music
```

The library name defaults to the directory name. Override it with `--name`.

The initialized library contains a `yt-maestro.json` manifest plus
`albums/`, `artists/`, and `downloads/` directories.

## Artists

An artist file defines reusable metadata. Its filename without `.json` is the
canonical artist ID used by album files:

```text
artists/beethoven.json
```

```json
{
  "name": "Ludwig van Beethoven",
  "default_genre": "Classical"
}
```

The ID is a stable configuration reference, while `name` is the display value
written to audio metadata. `default_genre` is used when an album does not
provide its own genre. An album therefore references the artist without
repeating its metadata:

```json
{
  "title": "Symphony No. 5",
  "artist": "beethoven"
}
```

Artist aliases are not part of the schema yet. Album creation accepts an
artist's display name and resolves it to the canonical ID before writing JSON.
Ambiguous matches are rejected rather than guessed.

## Create an album

Create an album draft interactively from a library directory:

```shell
yt-maestro album create
```

The command derives the album filename from its title and resolves the album
artist by display name. If the artist does not exist, it creates an artist file
using the display name and stores the entered genre as that artist's default.
For an existing artist, its default genre is offered by the genre prompt. The
album only stores a genre when it overrides an existing artist's default, and
is created with an empty `tracks` array for you to edit. Use `--library` when
running the command outside the library directory.

## Download an album

From a library directory, download an album by its filename without `.json`:

```shell
yt-maestro album download beethoven-symphony-no-5
```

Provide multiple references to download several albums, or use `--all` to
download every album in the library:

```shell
yt-maestro album download beethoven-symphony-no-5 mozart-requiem
yt-maestro album download --all
```

Use `--library` when running the command elsewhere:

```shell
yt-maestro album download beethoven-symphony-no-5 --library ~/Music
```

If any target tracks already exist, yt-maestro lists them and asks before
overwriting. Pass `--overwrite` to continue without prompting.

An album may use one shared source recording:

```json
{
  "title": "Symphony No. 5",
  "artist": "beethoven",
  "url": "https://youtu.be/full-recording",
  "tracks": [
    {"title": "I. Allegro con brio", "start": "0:04", "end": "8:20"},
    {"title": "II. Andante con moto", "start": "8:30", "end": "19:15"}
  ]
}
```

For ordinary albums, omit the shared URL and provide `url` on each track.
Tracks may also provide an `artist` ID; otherwise they inherit the album artist.
This allows compilation albums to use an album artist such as `various-artists`
while retaining each track's individual credit.

```json
{
  "title": "Best of Romantic",
  "artist": "various-artists",
  "tracks": [
    {
      "title": "Symphony No. 5",
      "artist": "beethoven",
      "url": "https://youtu.be/beethoven-recording"
    },
    {
      "title": "Hungarian Dance No. 5",
      "artist": "brahms",
      "url": "https://youtu.be/brahms-recording"
    }
  ]
}
```
