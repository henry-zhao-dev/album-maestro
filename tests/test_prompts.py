import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import call, patch

from album_maestro.commands import prompts


class NumberPromptTests(unittest.TestCase):
    @patch("builtins.input", return_value="")
    def test_empty_response_returns_default(self, input_mock):
        self.assertEqual(prompts.number("Track number", default=1), 1)
        input_mock.assert_called_once_with("Track number [1]: ")

    @patch("builtins.input", side_effect=("invalid", "12"))
    def test_invalid_response_prompts_again(self, input_mock):
        output = StringIO()

        with redirect_stdout(output):
            result = prompts.number("Track number", default=0)

        self.assertEqual(result, 12)
        self.assertEqual(
            input_mock.call_args_list,
            [call("Track number [0]: "), call("Track number [0]: ")],
        )
        self.assertEqual(output.getvalue(), "Please enter a whole number.\n")

    @patch("builtins.input", side_effect=("", "", "12"))
    def test_none_default_requires_a_number(self, input_mock):
        result = prompts.number("Track number")

        self.assertEqual(result, 12)
        self.assertEqual(
            input_mock.call_args_list,
            [
                call("Track number: "),
                call("Track number: "),
                call("Track number: "),
            ],
        )

    @patch("builtins.input", side_effect=("0", "4", "3"))
    def test_minimum_and_maximum_are_inclusive(self, input_mock):
        output = StringIO()

        with redirect_stdout(output):
            result = prompts.bounded_number("Disc number", minimum=1, maximum=3)

        self.assertEqual(result, 3)
        self.assertEqual(input_mock.call_count, 3)
        self.assertEqual(
            output.getvalue(),
            "Please enter a number from 1 to 3.\n"
            "Please enter a number from 1 to 3.\n",
        )

    def test_rejects_invalid_bounds(self):
        with self.assertRaisesRegex(ValueError, "minimum"):
            prompts.bounded_number("Track number", minimum=2, maximum=1)

    def test_rejects_default_outside_bounds(self):
        with self.assertRaisesRegex(ValueError, "default"):
            prompts.bounded_number(
                "Track number",
                minimum=1,
                maximum=3,
                default=0,
            )


class TextPromptTests(unittest.TestCase):
    @patch("builtins.input", return_value="")
    def test_override_text_keeps_blank_as_no_override(self, input_mock):
        self.assertEqual(prompts.override_text("Track artist", "Album artist"), "")
        input_mock.assert_called_once_with("Track artist [Album artist]: ")


if __name__ == "__main__":
    unittest.main()
