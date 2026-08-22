"""Orchestration for downloading, processing, and organizing recordings."""

import logging
import shutil
import tempfile
from collections.abc import Sequence
from pathlib import Path

from yt_maestro import audio, downloader, spec
from yt_maestro.models import TrackSpec


def process_specs(
    tracks: Sequence[TrackSpec], output_dir: str | Path = "."
) -> list[Path]:
    """Process tracks sequentially and return the successfully created files."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    for index, track in enumerate(tracks, start=1):
        logging.info("Processing %s of %s", index, len(tracks))
        try:
            output = process_track(track, destination)
        except spec.SpecError as error:
            logging.error("cannot process track %s: %s", index, error)
            continue
        if output is not None:
            outputs.append(output)
    return outputs


def process_track(track: TrackSpec, output_dir: str | Path = ".") -> Path | None:
    """Download, process, and organize one validated track."""

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".yt-maestro-", dir=destination) as temp:
        work_dir = Path(temp)
        downloaded = downloader.download_audio(track.url, work_dir, title=track.title)
        if downloaded is None:
            return None

        duration_ms = audio.audio_duration_ms(downloaded)
        start_ms, end_ms = spec.resolve_time_range(track, duration_ms)
        current = str(downloaded)

        if track.start_ms is not None or track.end_ms is not None:
            current = audio.trim_audio(
                current, work_dir / f"trim-{downloaded.name}", start_ms, end_ms
            )

        metadata = track.metadata()
        current = audio.add_metadata(
            current, work_dir / f"metadata-{downloaded.name}", metadata
        )

        if track.chapters:
            chapters = spec.resolve_chapters(track.chapters, start_ms, end_ms)
            current = audio.add_chapters(
                current, work_dir / f"chapters-{downloaded.name}", chapters
            )

        artist = metadata.get("artist", "Unknown Artist")
        album = metadata.get("album", "Unknown Album")
        final_path = destination / artist / album / downloaded.name
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(current, final_path)
        return final_path
