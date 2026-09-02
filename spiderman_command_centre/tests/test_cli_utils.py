"""
tests/test_cli_utils.py

Tests for the input layer's decision-menu primitive, prompt_choice.
Uses unittest.mock to feed scripted keystrokes to input() so these run
without a real terminal.
"""

import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import cli_utils


class PromptChoiceTests(unittest.TestCase):
    def test_returns_selected_item(self):
        with patch("builtins.input", side_effect=["2"]):
            result = cli_utils.prompt_choice("Pick one:", ["A", "B", "C"])
        self.assertEqual(result, "B")

    def test_cancel_returns_none(self):
        with patch("builtins.input", side_effect=["0"]):
            result = cli_utils.prompt_choice("Pick one:", ["A", "B"])
        self.assertIsNone(result)

    def test_no_cancel_option_when_disabled(self):
        # "0" isn't a valid choice at all when allow_cancel=False, so it
        # should be rejected and re-prompted, not treated as a selection.
        with patch("builtins.input", side_effect=["0", "1"]):
            result = cli_utils.prompt_choice("Pick one:", ["Only option"], allow_cancel=False)
        self.assertEqual(result, "Only option")

    def test_invalid_choice_is_rejected_then_recovers(self):
        with patch("builtins.input", side_effect=["99", "abc", "", "3"]):
            result = cli_utils.prompt_choice("Pick one:", ["A", "B", "C"])
        self.assertEqual(result, "C")

    def test_empty_items_returns_none_without_prompting(self):
        # Critical: must not call input() at all, or an unanswerable
        # menu could hang waiting for a choice that can never be valid.
        with patch("builtins.input") as mock_input:
            result = cli_utils.prompt_choice("Pick one:", [])
        mock_input.assert_not_called()
        self.assertIsNone(result)

    def test_returns_original_object_not_formatted_string(self):
        items = [{"id": 1, "name": "First"}, {"id": 2, "name": "Second"}]
        with patch("builtins.input", side_effect=["2"]):
            result = cli_utils.prompt_choice(
                "Pick one:", items, formatter=lambda item: item["name"]
            )
        self.assertEqual(result, items[1])

    def test_eof_raises_session_ended_not_infinite_loop(self):
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(cli_utils.SessionEnded):
                cli_utils.prompt_choice("Pick one:", ["A", "B"])


if __name__ == "__main__":
    unittest.main()
