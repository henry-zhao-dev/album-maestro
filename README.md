# YT Maestro

Declarative YouTube audio downloader with precision trimming and chaptering, 
tailored for classical music enthusiasts.

## Initialize a music library

Create a Git-friendly library interactively:

```shell
yt-maestro init
```

Pass a directory to create the library, or disable prompts for scripts:

```shell
yt-maestro init music --no-interaction
```

The initialized library contains a versioned `yt-maestro.json` manifest and
tracked `albums/` and `artists/` directories. Generated downloads and local
build state are added to the library's `.gitignore`.
