"""Tests for src/slugify.py (CLAUDE-4)."""

import re
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from slugify import slugify


class TestSlugify(unittest.TestCase):
    # ---- T-05: AC 1-4 and hyphen edges ----
    def test_ac1_basic_conversion(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_ac2_trims_and_lowercases(self):
        self.assertEqual(slugify("  Hello World  "), "hello-world")
        self.assertEqual(slugify("ABC"), "abc")

    def test_ac3_removes_special_characters(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")
        self.assertEqual(slugify("a@b#c"), "abc")

    def test_ac4_collapses_space_and_hyphen_runs(self):
        self.assertEqual(slugify("a   b"), "a-b")
        self.assertEqual(slugify("a---b"), "a-b")
        self.assertEqual(slugify("a - - b"), "a-b")

    def test_a1_a2_hyphen_edges_stripped(self):
        for text, expected in [("-Hello-", "hello"), ("--Hello--", "hello"),
                               ("-", ""), ("a-", "a")]:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), expected)

    def test_a1_hyphen_kept_inside(self):
        self.assertEqual(slugify("well-known"), "well-known")

    # ---- T-06: AC 5-6, idempotency, removal then collapse ----
    def test_ac5_empty_input(self):
        self.assertEqual(slugify(""), "")

    def test_ac5_all_invalid_input(self):
        for text in ["!!!", "   ", "---"]:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), "")

    def test_ac6_non_string_raises_type_error(self):
        for value in [None, 123, ["a"], b"a"]:
            with self.subTest(value=value):
                with self.assertRaises(TypeError) as ctx:
                    slugify(value)
                self.assertIn(type(value).__name__, str(ctx.exception))

    def test_idempotent(self):
        for text in ["  --A_b\t\nC-- ", "Hello, World!", "", "a - ! - b",
                     "x" * 5, "é a"]:
            with self.subTest(text=text):
                once = slugify(text)
                self.assertEqual(slugify(once), once)

    def test_removal_then_collapse(self):
        self.assertEqual(slugify("a - ! - b"), "a-b")

    def test_worked_example(self):
        self.assertEqual(slugify("  --A_b\t\nC-- "), "ab-c")

    # ---- T-07: whitespace and character classes ----
    def test_c10_tab_and_newline_are_separators(self):
        self.assertEqual(slugify("a\tb"), "a-b")
        self.assertEqual(slugify("a\nb"), "a-b")
        self.assertEqual(slugify("\t a \n"), "a")

    def test_a3_underscores_removed(self):
        self.assertEqual(slugify("snake_case"), "snakecase")
        self.assertEqual(slugify("a_ b"), "a-b")

    def test_a4_non_ascii_letters_removed(self):
        self.assertEqual(slugify("Café"), "caf")
        self.assertEqual(slugify("日本語"), "")

    def test_non_ascii_whitespace_removed(self):
        self.assertEqual(slugify("a b"), "ab")
        self.assertEqual(slugify("a b"), "ab")

    def test_kelvin_sign_removed(self):
        self.assertEqual(slugify("K"), "")

    def test_output_matches_charset(self):
        for text in ["Hello, World!", "  --A_b\t\nC-- ", "Café K",
                     "a b", "!!!", "x-y_z 9"]:
            with self.subTest(text=text):
                self.assertRegex(slugify(text), r"^[a-z0-9-]*$")

    def test_pure_no_input_mutation_and_deterministic(self):
        text = "  Hello, World!  "
        self.assertEqual(slugify(text), slugify(text))
        self.assertEqual(text, "  Hello, World!  ")

    # ---- T-08: NFR-2 ----
    def test_nfr2_10000_chars_under_50ms(self):
        chunk = "Ab c-- d!, "
        text = (chunk * (10000 // len(chunk) + 1))[:10000]
        self.assertEqual(len(text), 10000)
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            slugify(text)
            best = min(best, time.perf_counter() - start)
        self.assertLess(best, 0.050)


if __name__ == "__main__":
    unittest.main()
