# Example configurations

Album Maestro now stores its catalog in SQLite. These JSON files are retained
as migration fixtures while the database-backed track workflow is completed;
they are not copied into a new library.

Create a library and add album records through the CLI:

```shell
album-maestro init ~/Music/album-maestro-example
album-maestro create --library ~/Music/album-maestro-example
album-maestro list --library ~/Music/album-maestro-example
```

The YouTube URLs in the fixture files are placeholders.

Import an example album into SQLite with:

```shell
album-maestro import --json albums/beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro-example
```

Or import every example album at once:

```shell
album-maestro import --directory albums \
  --library ~/Music/album-maestro-example
```

Export an imported album back to JSON with:

```shell
album-maestro export beethoven-symphony-no-5 \
  --json beethoven-symphony-no-5.json \
  --library ~/Music/album-maestro-example
```

Then download the imported albums with:

```shell
album-maestro download --all --library ~/Music/album-maestro-example
```
