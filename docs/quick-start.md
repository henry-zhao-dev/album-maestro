# Quick start

This guide walks through a small interactive workflow: create an album, add
tracks, inspect the catalog, and then process local audio. It uses a single
committed source recording and the three movement ranges defined in
[`examples/albums/vivaldi-autumn.json`](../examples/albums/vivaldi-autumn.json).
The source file and its attribution are in
[`examples/sources/`](../examples/sources/).

Docker is the primary runtime for this walkthrough. If Docker is unavailable,
use the manual installation fallback documented in the main
[`README.md`](../README.md).

## 1. Set up Docker

From the repository checkout, build the image and install the user-level
launcher:

```shell
docker build --tag album-maestro:local .
./scripts/install-docker-cli
export PATH="$HOME/.local/bin:$PATH"
```

Add the `PATH` line to your shell profile if the installer reports that
`~/.local/bin` is not already on `PATH`. From this point forward, use
`album-maestro` directly; the launcher handles Docker for every command.

The launcher mounts `~/Music/album-maestro` by default. Export
`ALBUM_MAESTRO_LIB` to make the host directory explicit, or change its value
to use another directory:

```shell
export ALBUM_MAESTRO_LIB="$HOME/Music/album-maestro"
```

## 2. Create a library

Initialize the mounted library, then copy the committed Vivaldi recording into
its `sources/` directory:

```shell
album-maestro init .
mkdir -p "$ALBUM_MAESTRO_LIB/sources"
cp examples/sources/vivaldi-autumn.mp3 \
  "$ALBUM_MAESTRO_LIB/sources/"
```

## 3. Create an album

Run `album-maestro create` to enter the album metadata. New albums start with
no tracks:

```text
$ album-maestro create
Album title: The Four Seasons: Autumn
Album artist (optional): The Modena Chamber Orchestra
Album composer (optional): Antonio Vivaldi
Album genre: Classical
Album reference URL (optional):
Album file source (filename under sources/, optional): vivaldi-autumn.mp3

Album created: the-four-seasons-autumn
The album has no tracks yet. Use 'edit' to add tracks.
```

> Library commands use the current directory by default. If you run one from
> elsewhere, pass `--library DIRECTORY`, for example:
>
> ```shell
> album-maestro list --library /library/another-library
> ```

## 4. Add tracks

Run `album-maestro edit the-four-seasons-autumn` to add, change, or remove
tracks. The tracks inherit the album-level artist and composer, and leave their
local source blank so they inherit the album's single source recording. Enter
source paths as bare filenames; they must already exist in the library's
`sources/` directory.

```text
$ album-maestro edit the-four-seasons-autumn
...
Track actions: [a]dd, [e]dit, [r]emove, [d]one
Choose an action: a
Track title: I. Allegro
...
Track start (optional): 0:00
Track end (optional): 5:29
Added track 1.
...
Choose an action: a
Track title: II. Adagio molto
...
Track start (optional): 5:29
Track end (optional): 8:50
Added track 2.
...
Choose an action: a
Track title: III. Allegro
...
Track start (optional): 8:50
Track end (optional): 12:13
Added track 3.
...
Choose an action: d
```

## 5. List the albums

Run `album-maestro list` for a compact overview of the catalog entry:

```text
$ album-maestro list
REFERENCE                TITLE                     ARTIST                        GENRE      TRACKS
-----------------------  ------------------------  ----------------------------  ---------  ------
the-four-seasons-autumn  The Four Seasons: Autumn  The Modena Chamber Orchestra  Classical  3
```

## 6. Show album details

Use `album-maestro show the-four-seasons-autumn` to verify the album metadata and
the track ranges defined for the shared source:

```text
$ album-maestro show the-four-seasons-autumn
Title:          The Four Seasons: Autumn
Artist:         The Modena Chamber Orchestra
Album artist:   The Modena Chamber Orchestra
Composer:       Antonio Vivaldi
Genre:          Classical

Reference URL:  —
File source:    vivaldi-autumn.mp3

TRACKS
  #  TITLE                                         START    END
  1  I. Allegro                                    0:00     5:29
  2  II. Adagio molto                              5:29     8:50
  3  III. Allegro                                  8:50     12:13
```

## 7. Process the album

Once the catalog entry looks right, run
`album-maestro process the-four-seasons-autumn` to create tagged files from the
single local source:

```text
$ album-maestro process the-four-seasons-autumn
[INFO] Processed the-four-seasons-autumn track 1: /Users/you/Music/album-maestro/tracks/The Modena Chamber Orchestra/The Four Seasons: Autumn/I. Allegro.mp3
[INFO] Processed the-four-seasons-autumn track 2: /Users/you/Music/album-maestro/tracks/The Modena Chamber Orchestra/The Four Seasons: Autumn/II. Adagio molto.mp3
[INFO] Processed the-four-seasons-autumn track 3: /Users/you/Music/album-maestro/tracks/The Modena Chamber Orchestra/The Four Seasons: Autumn/III. Allegro.mp3
```

Import the generated files into your preferred music player, such as Apple
Music or VLC, and play the album to verify the tags, track titles, and timing.
