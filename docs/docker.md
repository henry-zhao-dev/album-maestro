# Docker

Docker is an optional way to run Album Maestro with Python, Poetry, FFmpeg, and
ffprobe supplied by the image. The catalog and audio remain outside the image:
mount a library directory at `/library` when running a command.

## Build the image

From the repository checkout:

```shell
docker build --tag album-maestro:local .
```

The build uses the checked-in `poetry.lock` file and keeps Poetry available in
the resulting image. The Poetry version can be overridden when experimenting:

```shell
docker build --build-arg POETRY_VERSION=2.4.1 \
  --tag album-maestro:local .
```

## Run commands

Set the library directory on the host, then initialize it through the
container:

```shell
export ALBUM_LIBRARY="$HOME/Music/album-maestro"
mkdir -p "$ALBUM_LIBRARY"

docker run --rm --user "$(id -u):$(id -g)" -it \
  --volume "$ALBUM_LIBRARY:/library" \
  --workdir /library \
  album-maestro:local init .
```

Copy local source files into `$ALBUM_LIBRARY/sources/`, then use the same mount
for interactive catalog commands:

```shell
docker run --rm --user "$(id -u):$(id -g)" -it \
  --volume "$ALBUM_LIBRARY:/library" \
  --workdir /library \
  album-maestro:local create

docker run --rm --user "$(id -u):$(id -g)" -it \
  --volume "$ALBUM_LIBRARY:/library" \
  --workdir /library \
  album-maestro:local edit ALBUM
```

Batch processing does not need an interactive terminal:

```shell
docker run --rm --user "$(id -u):$(id -g)" \
  --volume "$ALBUM_LIBRARY:/library" \
  --workdir /library \
  album-maestro:local process --all
```

The `--user` option makes files created under the bind mount belong to the
invoking host user on Linux. Docker Desktop users may omit it if their shared
filesystem does not require matching numeric ownership.

The image does not contain a database, source audio, or generated tracks. It
is therefore safe to rebuild or replace the image without affecting a library.
