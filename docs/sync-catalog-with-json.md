# Syncing the catalog with JSON specs

Prefer a file to a long series of prompts? Define album metadata and track
ranges in JSON, import the specification into SQLite, process local audio, and
export the catalog again when you want a portable copy.

The repository includes two example specifications in
[`examples/albums/`](../examples/albums/) and three committed recordings in
[`examples/sources/`](../examples/sources/), so the walkthrough needs no
download. `classical-favorites.json` combines separate Boccherini and Mozart
recordings, while `vivaldi-autumn.json` shows how one recording becomes three
player-friendly tracks through JSON time ranges.

## JSON specifications

An album specification needs a title, genre, and at least one track. Albums and
tracks can define artists, composers, genres, reference URLs, local sources,
timestamps, and chapters. Album values provide defaults, while track values
override them. An album without an artist uses `Various Artists` in output
metadata.

Reference `url` values are catalog metadata only; Album Maestro never downloads
audio from them. Local audio must already exist inside the library's `sources/`
directory. A `file_source` can be set on the album or a track, and paths that
escape `sources/` are rejected. Chapters can be imported and processed, but the
interactive prompt does not edit them yet.

## Run the examples

From the repository checkout, install the dependencies and activate Poetry's
environment once:

```shell
poetry install
eval $(poetry env activate)
```

From the repository root, create a library and copy the example audio into it:

```shell
album-maestro init ~/Music/album-maestro-example
cp examples/sources/vivaldi-autumn.mp3 \
  examples/sources/boccherini-minuet.ogg \
  examples/sources/mozart-piano-sonata-no-11-iii.ogg \
  ~/Music/album-maestro-example/sources/
```

> The source files are committed, so no download is required. Their licensing
> or public-domain status has been checked, and attribution is provided in
> [`examples/sources/ATTRIBUTION.md`](../examples/sources/ATTRIBUTION.md). If
> you prefer to fetch fresh copies from Wikimedia Commons, run:
>
> ```shell
> curl --fail --location --output examples/sources/boccherini-minuet.ogg \
>   "https://commons.wikimedia.org/wiki/Special:FilePath/Boccerini_Op11_n%C2%B05_G275_Satz3_Minuett.ogg"
> curl --fail --location --output examples/sources/mozart-piano-sonata-no-11-iii.ogg \
>   "https://commons.wikimedia.org/wiki/Special:FilePath/Mozart-Marsz_turecki-(Romuald_Greiss).ogg"
> curl --fail --location --output examples/sources/vivaldi-autumn.mp3 \
>   "https://commons.wikimedia.org/wiki/Special:FilePath/Vivaldi_The_Four_Seasons,_Op._8_-_The_Modena_Chamber_Orchestra_-_Violin_Concerto_in_F_major_RV_293_Autumn.mp3"
> ```

Import the Vivaldi example into SQLite with:

```shell
album-maestro import --json examples/albums/vivaldi-autumn.json \
  --library ~/Music/album-maestro-example
```

Or import every example album at once:

```shell
album-maestro import --directory examples/albums \
  --library ~/Music/album-maestro-example
```

Existing album references are rejected unless `--overwrite` is passed. A
directory import continues after individual failures and returns a failure
status if any file could not be imported.

Process the Vivaldi example into tagged track files:

```shell
album-maestro process the-four-seasons-autumn \
  --library ~/Music/album-maestro-example
```

Process the Classical Favorites example:

```shell
album-maestro process classical-favorites \
  --library ~/Music/album-maestro-example
```

Export an imported album back to JSON with:

```shell
album-maestro export the-four-seasons-autumn \
  --json vivaldi-autumn.json \
  --library ~/Music/album-maestro-example
```

Directory exports use `<album-reference>.json`. Existing files are not replaced
unless `--overwrite` is passed, and exports preserve defaults, overrides,
timestamps, and chapters.
