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
