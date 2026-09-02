import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from yt_dlp.utils import DownloadError

from album_maestro import downloader


class DownloadTests(unittest.TestCase):
    @patch("album_maestro.downloader.yt_dlp.YoutubeDL")
    def test_returns_post_processed_path(self, youtube_dl):
        client = youtube_dl.return_value.__enter__.return_value

        with tempfile.TemporaryDirectory() as output_dir:
            downloaded_path = Path(output_dir) / "recording.m4a"
            downloaded_path.touch()
            client.extract_info.return_value = {
                "requested_downloads": [{"filepath": str(downloaded_path)}]
            }
            result = downloader.download_audio("https://example.com", output_dir)

        self.assertEqual(result, downloaded_path)
        options = youtube_dl.call_args.args[0]
        postprocessor = options["postprocessors"][0]
        self.assertEqual(postprocessor["preferredcodec"], "m4a")
        self.assertEqual(postprocessor["preferredquality"], "192")
        self.assertNotIn("postprocessor_args", options)

    @patch("album_maestro.downloader.yt_dlp.YoutubeDL")
    def test_download_error_is_exposed_to_the_pipeline(self, youtube_dl):
        client = youtube_dl.return_value.__enter__.return_value
        client.extract_info.side_effect = DownloadError("unavailable")

        with (
            tempfile.TemporaryDirectory() as output_dir,
            self.assertRaisesRegex(downloader.DownloaderError, "unavailable"),
        ):
            downloader.download_audio("https://example.com", output_dir)


if __name__ == "__main__":
    unittest.main()
