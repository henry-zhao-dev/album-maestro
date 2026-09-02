# Example configurations

These files demonstrate the Album Maestro artist and album formats. They are
intended to be copied into an initialized library, not downloaded as-is: every
YouTube URL is a placeholder.

```shell
album-maestro init ~/Music/album-maestro-example
cp examples/artists/*.json ~/Music/album-maestro-example/artists/
cp examples/albums/*.json ~/Music/album-maestro-example/albums/
```

Replace the placeholder URLs, then run:

```shell
album-maestro album download --all --library ~/Music/album-maestro-example
```
