# Example configurations

Album Maestro now stores its catalog in SQLite. These JSON files are retained
as migration fixtures while the database-backed track workflow is completed;
they are not copied into a new library.

Create a library and add album records through the CLI:

```shell
album-maestro init ~/Music/album-maestro-example
album-maestro album create --library ~/Music/album-maestro-example
album-maestro album list --library ~/Music/album-maestro-example
```

The YouTube URLs in the fixture files are placeholders.

The future import workflow will make these examples directly usable.

For the existing JSON-backed download workflow, run:

```shell
album-maestro album download --all --library ~/Music/album-maestro-example
```
