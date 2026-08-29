"""Pipelines that turn catalog specifications into downloaded audio files."""

from yt_maestro.pipelines.album import download_album, existing_album_tracks

__all__ = ["download_album", "existing_album_tracks"]
