# YT Maestro

Declarative YouTube audio downloader with precision trimming and chaptering, 
tailored for classical music enthusiasts.

## Initialize a music library

Create a library interactively:

```shell
yt-maestro init
```

Pass a directory to create the library, or disable prompts for scripts:

```shell
yt-maestro init music --no-interaction
```

The initialized library contains a `yt-maestro.json` manifest plus
`albums/`, `artists/`, and `downloads/` directories.

## Download an album

From a library directory, download an album by its filename without `.json`:

```shell
yt-maestro album download beethoven-symphony-no-5
```

Use `--library` when running the command elsewhere:

```shell
yt-maestro album download beethoven-symphony-no-5 --library ~/Music
```

An artist file such as `artists/beethoven.json` provides shared metadata:

```json
{
  "name": "Ludwig van Beethoven",
  "default_genre": "Classical"
}
```

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
