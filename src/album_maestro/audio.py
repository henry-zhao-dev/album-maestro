"""Tool-independent audio inspection and editing operations."""

import math
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

from album_maestro.models import Chapter


class AudioError(RuntimeError):
    """Raised when an external audio operation cannot be completed."""


def audio_duration_ms(path: str | Path) -> int:
    """Return the reported duration in milliseconds, or zero if malformed."""

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    output = _run_command(command)

    try:
        duration_seconds = float(output)
    except ValueError:
        return 0
    if not math.isfinite(duration_seconds) or duration_seconds < 0:
        return 0
    return math.floor(duration_seconds * 1000)


def trim_audio(
    input_path: str | Path,
    output_path: str | Path,
    start_ms: int,
    end_ms: int,
    *,
    re_encode: bool = False,
) -> str:
    """Copy the selected time range into a new audio file."""

    input_path, output_path = str(input_path), str(output_path)
    if start_ms < 0 or end_ms <= start_ms:
        raise ValueError(
            "start_ms must be non-negative and end_ms must be greater than start_ms"
        )

    command = _ffmpeg_command([input_path])
    command.extend(
        [
            "-ss",
            _milliseconds_to_seconds(start_ms),
            "-t",
            _milliseconds_to_seconds(end_ms - start_ms),
            "-map",
            "0",
        ]
    )
    if not re_encode:
        command.extend(["-c", "copy"])
    command.append(output_path)
    _run_command(command)
    return output_path


def add_metadata(
    input_path: str | Path,
    output_path: str | Path,
    metadata: Mapping[str, str],
) -> str:
    """Copy an audio file with metadata tags applied."""

    input_path, output_path = str(input_path), str(output_path)
    if not metadata:
        return input_path

    command = _ffmpeg_command([input_path])
    for key, value in metadata.items():
        command.extend(["-metadata", f"{key}={value}"])
    command.extend(["-map", "0", "-c", "copy", output_path])
    _run_command(command)
    return output_path


def add_chapters(
    input_path: str | Path,
    output_path: str | Path,
    chapters: Sequence[Chapter],
) -> str:
    """Copy an audio file with chapter metadata applied."""

    input_path, output_path = str(input_path), str(output_path)
    if not chapters:
        return input_path

    metadata_file = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".ffmeta", delete=False
    )
    metadata_path = metadata_file.name
    try:
        with metadata_file:
            print(";FFMETADATA1", file=metadata_file)
            for chapter in chapters:
                print(_chapter_tag(chapter), file=metadata_file)

        # Preserve tags from the audio input while taking chapters from the
        # generated ffmetadata input.
        command = _ffmpeg_command([input_path, metadata_path])
        command.extend(
            [
                "-map",
                "0",
                "-map_metadata",
                "0",
                "-map_chapters",
                "1",
                "-c",
                "copy",
                output_path,
            ]
        )
        _run_command(command)
        return output_path
    finally:
        try:
            Path(metadata_path).unlink()
        except FileNotFoundError:
            pass


def _ffmpeg_command(input_paths: Sequence[str | Path]) -> list[str]:
    """Build the common portion of an FFmpeg command."""

    command = ["ffmpeg", "-nostdin", "-y", "-v", "error"]
    for path in input_paths:
        command.extend(["-i", str(path)])
    return command


def _run_command(command: Sequence[str]) -> str:
    """Run a media command and return its stripped combined output."""

    if not command:
        raise ValueError("media command must not be empty")
    try:
        output = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        return output.strip()
    except FileNotFoundError as error:
        raise AudioError(f"external command not found: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        details = error.output.strip() if error.output else "no error output"
        raise AudioError(
            f"{command[0]} failed with exit code {error.returncode}: {details}"
        ) from error


def _milliseconds_to_seconds(milliseconds: int) -> str:
    """Format milliseconds as the seconds syntax accepted by FFmpeg."""

    return f"{milliseconds / 1000:.3f}"


def _chapter_tag(chapter: Chapter) -> str:
    """Render one resolved chapter in FFmpeg metadata format."""

    if chapter.end_ms is None or chapter.title is None:
        raise ValueError("chapter must have a title and end time before embedding")
    return "\n".join(
        (
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={chapter.start_ms}",
            f"END={chapter.end_ms}",
            f"TITLE={_escape_metadata(chapter.title)}",
        )
    )


def _escape_metadata(value: str) -> str:
    """Escape characters with special meaning in FFmpeg metadata."""

    value = value.replace("\r\n", "\n").replace("\r", "\n")
    for character in ("\\", "=", ";", "#"):
        value = value.replace(character, f"\\{character}")
    return value.replace("\n", "\\\n")
