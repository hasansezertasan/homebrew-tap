"""Tests for ``scripts/gen_readme_packages.py`` (stdlib ``unittest``, no network).

Exercises the pure parsing/rendering helpers and asserts the checked-in
README.md is up to date, so a formula/cask added without regenerating the table
fails CI. Run with ``python -m unittest discover -s tests`` from the repo root.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_readme_packages as gen  # noqa: E402


class FieldTest(unittest.TestCase):
    def test_extracts_desc_and_homepage(self) -> None:
        text = '  desc "Does a thing"\n  homepage "https://example.com"\n'
        self.assertEqual(gen.field(text, "desc"), "Does a thing")
        self.assertEqual(gen.field(text, "homepage"), "https://example.com")

    def test_missing_field_returns_empty(self) -> None:
        self.assertEqual(gen.field("class Foo < Formula\nend\n", "desc"), "")


class EscapeCellTest(unittest.TestCase):
    def test_escapes_pipe(self) -> None:
        self.assertEqual(gen.escape_cell("a | b"), "a \\| b")

    def test_leaves_plain_text_untouched(self) -> None:
        self.assertEqual(gen.escape_cell("plain description"), "plain description")


class SpliceTest(unittest.TestCase):
    def test_replaces_only_marked_region(self) -> None:
        readme = f"intro\n{gen.BEGIN}\nold\n{gen.END}\noutro\n"
        result = gen.splice(readme, f"{gen.BEGIN}\nnew\n{gen.END}")
        self.assertEqual(result, f"intro\n{gen.BEGIN}\nnew\n{gen.END}\noutro\n")

    def test_missing_markers_exits(self) -> None:
        with self.assertRaises(SystemExit):
            gen.splice("no markers here", "table")


class TableTest(unittest.TestCase):
    def test_lists_every_formula_and_cask_once(self) -> None:
        table = gen.build_table()
        # keycast ships as both; it must appear exactly once, combined.
        self.assertEqual(table.count("[`keycast`]"), 1)
        self.assertIn("Formula + Cask", table)


class ReadmeFreshnessTest(unittest.TestCase):
    def test_readme_table_is_current(self) -> None:
        current = gen.README.read_text()
        updated = gen.splice(current, gen.build_table())
        self.assertEqual(current, updated,
                         "README.md packages table is stale; run "
                         "`python scripts/gen_readme_packages.py`")


if __name__ == "__main__":
    unittest.main()
