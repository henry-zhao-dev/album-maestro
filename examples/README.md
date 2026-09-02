# Example configurations

These files demonstrate the YT Maestro artist and album formats. They are
intended to be copied into an initialized library, not downloaded as-is: every
YouTube URL is a placeholder.

```shell
yt-maestro init ~/Music/yt-maestro-example
cp examples/artists/*.json ~/Music/yt-maestro-example/artists/
cp examples/albums/*.json ~/Music/yt-maestro-example/albums/
```

Replace the placeholder URLs, then run:

```shell
yt-maestro album download --all --library ~/Music/yt-maestro-example
```
