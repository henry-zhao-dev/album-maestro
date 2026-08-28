"""Tool-independent audio inspection and editing operations."""

import logging
import math
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence

from yt_maestro.models import Chapter

PathType = str | os.PathLike[str]


def audio_duration_ms(path: PathType) -> int:
    """Return the container-reported duration in milliseconds, or zero."""

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        os.fspath(path),
    ]
    output = _run_command(command)
    if output is None:
        return 0

    try:
        duration_seconds = float(output)
    except ValueError:
        return 0
    if not math.isfinite(duration_seconds) or duration_seconds < 0:
        return 0
    return math.floor(duration_seconds * 1000)


def trim_audio(
    input_path: PathType,
    output_path: PathType,
    start_ms: int,
    end_ms: int,
    *,
    reencode: bool = False,
) -> str:
    """Trim an audio file, returning the input path if no output was produced."""

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)
    duration_ms = audio_duration_ms(input_path)
    if start_ms == 0 and end_ms == duration_ms:
        return input_path

    command = _base_command([input_path])
    command.extend(
        ["-ss", f"{start_ms / 1000:.3f}", "-to", f"{end_ms / 1000:.3f}", "-map", "0"]
    )
    if not reencode:
        command.extend(["-c", "copy"])
    command.append(output_path)
    return input_path if _run_command(command) is None else output_path


def add_metadata(
    input_path: PathType, output_path: PathType, metadata: Mapping[str, str]
) -> str:
    """Copy an audio file with metadata tags applied."""

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)
    if not metadata:
        return input_path

    command = _base_command([input_path])
    for key, value in metadata.items():
        command.extend(["-metadata", f"{key}={value}"])
    command.extend(["-map", "0", "-c", "copy", output_path])
    return input_path if _run_command(command) is None else output_path


def add_chapters(
    input_path: PathType, output_path: PathType, chapters: Sequence[Chapter]
) -> str:
    """Copy an audio file with chapter metadata applied."""

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)
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

        command = _base_command([input_path, metadata_path])
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
        return input_path if _run_command(command) is None else output_path
    finally:
        try:
            os.remove(metadata_path)
        except FileNotFoundError:
            pass


def _base_command(input_paths: Sequence[PathType], *, quiet: bool = True) -> list[str]:
    command = ["ffmpeg", "-y"]
    if quiet:
        command.extend(["-v", "error"])
    for path in input_paths:
        command.extend(["-i", os.fspath(path)])
    return command


def _run_command(command: Sequence[str]) -> str | None:
    if not command:
        return None
    try:
        output = subprocess.check_output(command, text=True, stderr=subprocess.STDOUT)
        return output.strip()
    except FileNotFoundError:
        logging.error("%s is not installed or not in PATH", command[0])
    except subprocess.CalledProcessError as error:
        logging.error(
            "%s failed (exit %s): %s", command[0], error.returncode, error.output
        )
    return None


def _chapter_tag(chapter: Chapter) -> str:
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
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    for character in ("\\", "=", ";", "#"):
        value = value.replace(character, f"\\{character}")
    return value.replace("\n", "\\\n")
