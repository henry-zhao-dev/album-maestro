import logging
import math
import os
import subprocess
from dataclasses import dataclass
from typing import Union

QUIET_FFMPEG_LOG = True

PathType = Union[str, os.PathLike]


@dataclass
class Chapter:
    start_ms: int
    end_ms: int
    title: str

    def ffmpeg_tag(self) -> str:
        return '\n'.join([
            "[CHAPTER]",
            "TIMEBASE=1/1000",
            f"START={self.start_ms}",
            f"END={self.end_ms}",
            f"TITLE={self.title}"
        ])


def audio_duration_ms(path: PathType) -> int:
    """
    Returns the container-reported duration in milliseconds.
    Works for .m4a/.mp4/.mp3/.flac/etc.
    """

    path = os.fspath(path)
    ffprobe_cmd = [
        "ffprobe",
        # Only show fatal errors (suppress logs/info)
        "-v", "error",
        # Extract only the "duration" field from the format section
        "-show_entries", "format=duration",
        # Output format: plain text, no section wrappers, no keys
        # e.g., prints just "123.456" instead of "duration=123.456"
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]

    out = run_subprocess(ffprobe_cmd)
    try:
        return math.floor(float(out) * 1000)
    except (TypeError, ValueError):
        return 0


def trim_audio(input_path: PathType, output_path: PathType,
               start_ms: int, end_ms: int) -> str:
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

    ffmpeg_cmd = base_ffmpeg_command([input_path])
    ffmpeg_cmd.extend([
        "-ss", f"{start_ms / 1000:.3f}",
        "-to", f"{end_ms / 1000:.3f}",
        "-map", "0", "-c", "copy", output_path
    ])

    return input_path if run_subprocess(ffmpeg_cmd) is None else output_path


def add_metadata(input_path: PathType, output_path: PathType,
                 metadata: dict[str, str]) -> str:
    """
    Add metadata tags to an audio file using ffmpeg.

    :param input_path: Path to the input file.
    :param output_path: Path to the output file.
    :param metadata: Dictionary of metadata fields (e.g. {"artist": "Bach"}).
    :return: output_path if successful, otherwise input_path.
    """

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)

    if not metadata:
        return input_path

    ffmpeg_cmd = base_ffmpeg_command([input_path])
    for key, value in metadata.items():
        ffmpeg_cmd.extend(["-metadata", f"{key}={value}"])
    ffmpeg_cmd.extend(["-map", "0", "-c", "copy", output_path])

    return input_path if run_subprocess(ffmpeg_cmd) is None else output_path


def add_chapters(input_path: PathType, output_path: PathType,
                 chapters: list[Chapter]) -> str:
    """
    Embeds chapter metadata into an audio file using ffmpeg.

    :param input_path: Path to the source audio file.
    :param output_path: Path where the chaptered audio file will be written.
    :param chapters: List of Chapter objects with start/end/title.
    :return: Path to the output file.
    """

    input_path, output_path = os.fspath(input_path), os.fspath(output_path)
    ffmeta_path = f"{output_path}.ffmeta"

    with open(ffmeta_path, "w") as ffmeta_file:
        print(";FFMETADATA1", file=ffmeta_file)
        for ch in chapters:
            print(ch.ffmpeg_tag(), file=ffmeta_file)

    ffmpeg_cmd = base_ffmpeg_command([input_path, ffmeta_path])
    ffmpeg_cmd.extend([
        "-map_metadata", "0",
        "-map_chapters", "1",
        "-c", "copy",
        output_path
    ])
    run_subprocess(ffmpeg_cmd)

    if os.path.exists(ffmeta_path):
        os.remove(ffmeta_path)

    return output_path


def base_ffmpeg_command(input_paths: list[PathType]) -> list[str]:
    """
    Provides a common foundation of all ffmpeg commands.
    :param input_paths: Path(s) to the input audio file(s).
    """

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",  # Overwrite existing files
    ]

    if QUIET_FFMPEG_LOG:
        ffmpeg_cmd.extend(["-v", "error"])

    for path in input_paths:
        ffmpeg_cmd.extend(["-i", os.fspath(path)])

    return ffmpeg_cmd


def run_subprocess(cmd: list[str], program: str | None = None) -> str | None:
    """
    Runs a subprocess command safely and returns its stdout.

    :param cmd: Command to run as a list of strings.
    :param program: Optional program name for logging context.
                    Defaults to cmd[0] if set to None.
    :return: The stdout output as a string if successful, otherwise None.
    """

    if not cmd:
        return None
    if not program:
        program = cmd[0]

    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return out.strip()
    except FileNotFoundError:
        logging.error(f"{program} is not installed or not in PATH")
    except subprocess.CalledProcessError as e:
        logging.error(f"{program} failed (exit {e.returncode}): {e.output}")
    except Exception:
        logging.exception(f"Unexpected error running {program}")

    return None
