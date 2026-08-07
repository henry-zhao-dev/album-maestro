"""Utilities for inspecting and editing audio files with FFmpeg."""

import logging
import math
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

PathType = str | os.PathLike[str]


@dataclass(frozen=True)
class Chapter:
    """
    Represents an audio chapter with millisecond timestamps.

    :param start_ms: Chapter start timestamp in milliseconds.
    :param end_ms: Chapter end timestamp in milliseconds.
    :param title: Chapter title.
    """

    start_ms: int
    end_ms: int
    title: str

    def ffmpeg_tag(self) -> str:
        """
        Formats the chapter as FFmpeg metadata.

        :return: Chapter metadata in FFmpeg's FFMETADATA format.
        """

        metadata = (
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={self.start_ms}",
            f"END={self.end_ms}",
            f"TITLE={self.title}",
        )
        return "\n".join(metadata)


def audio_duration_ms(path: PathType) -> int:
    """
    Returns the container-reported duration in milliseconds.

    :param path: Path to the audio file.
    :return: Duration in milliseconds, or 0 if ffprobe fails or reports an
             invalid duration.
    """

    path = os.fspath(path)
    ffprobe_cmd = [
        "ffprobe",
        # Only show fatal errors (suppress logs/info)
        "-v",
        "error",
        # Extract only the "duration" field from the format section
        "-show_entries",
        "format=duration",
        # Output format: plain text, no section wrappers, no keys
        # e.g., prints just "123.456" instead of "duration=123.456"
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        path,
    ]

    out = _run_subprocess(ffprobe_cmd)
    if out is None:
        return 0

    try:
        return math.floor(float(out) * 1000)
    except ValueError:
        return 0


def trim_audio(
    input_path: PathType,
    output_path: PathType,
    start_ms: int,
    end_ms: int,
) -> str:
    """
    Trims an audio file to a given time range without re-encoding.

    :param input_path: Path to the input audio file.
    :param output_path: Path where the trimmed audio file will be written.
    :param start_ms: Start timestamp for the trim in milliseconds.
    :param end_ms: End timestamp for the trim in milliseconds.
    :return: Path to the trimmed file (output_path). If no trim is possible,
             the original input_path is returned unchanged.
    """

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)

    duration_ms = audio_duration_ms(input_path)
    if start_ms == 0 and end_ms == duration_ms:
        return input_path

    ffmpeg_cmd = _base_ffmpeg_command([input_path])
    ffmpeg_cmd.extend(
        [
            "-ss",
            f"{start_ms / 1000:.3f}",
            "-to",
            f"{end_ms / 1000:.3f}",
            # Include every stream from the first input, such as audio and cover art.
            "-map",
            "0",
            "-c",
            "copy",
            output_path,
        ]
    )

    return input_path if _run_subprocess(ffmpeg_cmd) is None else output_path


def add_metadata(
    input_path: PathType, output_path: PathType, metadata: Mapping[str, str]
) -> str:
    """
    Adds metadata tags to an audio file using FFmpeg.

    :param input_path: Path to the input file.
    :param output_path: Path to the output file.
    :param metadata: Metadata fields (e.g. {"artist": "Bach"}).
    :return: output_path if successful, otherwise input_path.
    """

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)

    if not metadata:
        return input_path

    ffmpeg_cmd = _base_ffmpeg_command([input_path])
    for key, value in metadata.items():
        ffmpeg_cmd.extend(["-metadata", f"{key}={value}"])
    ffmpeg_cmd.extend(["-map", "0", "-c", "copy", output_path])

    return input_path if _run_subprocess(ffmpeg_cmd) is None else output_path


def add_chapters(
    input_path: PathType, output_path: PathType, chapters: Sequence[Chapter]
) -> str:
    """
    Embeds chapter metadata into an audio file using FFmpeg.

    :param input_path: Path to the source audio file.
    :param output_path: Path where the chaptered audio file will be written.
    :param chapters: Chapters to embed in the audio file.
    :return: Path to the output file.
    """

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)
    ffmeta_path = f"{output_path}.ffmeta"

    with open(ffmeta_path, "w") as ffmeta_file:
        print(";FFMETADATA1", file=ffmeta_file)
        for chapter in chapters:
            print(chapter.ffmpeg_tag(), file=ffmeta_file)

    ffmpeg_cmd = _base_ffmpeg_command([input_path, ffmeta_path])
    ffmpeg_cmd.extend(
        ["-map_metadata", "0", "-map_chapters", "1", "-c", "copy", output_path]
    )
    _run_subprocess(ffmpeg_cmd)

    if os.path.exists(ffmeta_path):
        os.remove(ffmeta_path)

    return output_path


def _base_ffmpeg_command(
    input_paths: Sequence[PathType], quiet: bool = True
) -> list[str]:
    """
    Builds the common foundation for FFmpeg commands.

    :param input_paths: Path(s) to the input audio file(s).
    :param quiet: Only display FFmpeg errors when true.
    :return: Base FFmpeg command arguments.
    """

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Overwrite existing files
    ]

    if quiet:
        ffmpeg_cmd.extend(["-v", "error"])

    for path in input_paths:
        ffmpeg_cmd.extend(["-i", os.fspath(path)])

    return ffmpeg_cmd


def _run_subprocess(cmd: Sequence[str], program: str | None = None) -> str | None:
    """
    Runs a subprocess command safely and returns its stdout.

    :param cmd: Command and arguments to run.
    :param program: Optional program name for logging context.
                    Defaults to cmd[0] if set to None.
    :return: The stdout output as a string if successful, otherwise None.
    """

    if not cmd:
        return None
    if program is None:
        program = cmd[0]

    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return out.strip()
    except FileNotFoundError:
        logging.error("%s is not installed or not in PATH", program)
    except subprocess.CalledProcessError as error:
        logging.error(
            "%s failed (exit %s): %s", program, error.returncode, error.output
        )
    except Exception:
        logging.exception("Unexpected error running %s", program)

    return None
