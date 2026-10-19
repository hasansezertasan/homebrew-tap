"""Tests for ``scripts/gen_readme_packages.py`` (stdlib ``unittest``, no network).

Exercises the pure parsing/rendering helpers and asserts the checked-in
README.md is up to date, so a formula/cask added without regenerating the table
fails CI. Run with ``python -m unittest discover -s tests`` from the repo root.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_collapses_newlines_and_whitespace(self) -> None:
        self.assertEqual(gen.escape_cell("first\nsecond   third"), "first second third")


class SourceTest(unittest.TestCase):
    def test_formula_is_pypi(self) -> None:
        self.assertEqual(gen.source(True, False), "PyPI")

    def test_cask_is_github_releases(self) -> None:
        self.assertEqual(gen.source(False, True), "GitHub Releases")

    def test_both_lists_both_sources(self) -> None:
        self.assertEqual(gen.source(True, True), "PyPI + GitHub Releases")


class LinksTest(unittest.TestCase):
    def test_formula_gets_pypi_link(self) -> None:
        out = gen.links(True, "widget", "https://example.com")
        self.assertEqual(out, " ([PyPI](https://pypi.org/project/widget/))")

    def test_cask_gets_no_link(self) -> None:
        self.assertEqual(gen.links(False, "widget", "https://example.com"), "")

    def test_pypi_homepage_gets_no_link(self) -> None:
        out = gen.links(True, "widget", "https://pypi.org/project/widget/")
        self.assertEqual(out, "")


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
        formula = {"example": {"desc": "Example CLI", "homepage": "https://example.com"}}
        cask = {"example": {"desc": "Example app", "homepage": "https://example.com"}}
        with patch.object(gen, "collect", side_effect=[formula, cask]):
            table = gen.build_table()
        self.assertEqual(table.count("[`example`]"), 1)
        self.assertIn("Formula + Cask", table)
        self.assertIn("PyPI + GitHub Releases", table)

    def test_formula_row_links_pypi(self) -> None:
        formula = {"widget": {"desc": "Does a thing", "homepage": "https://example.com"}}
        with patch.object(gen, "collect", side_effect=[formula, {}]):
            table = gen.build_table()
        self.assertIn("[PyPI](https://pypi.org/project/widget/)", table)
        self.assertIn("| PyPI |", table)


class EmptyTapTest(unittest.TestCase):
    def test_empty_tap_still_has_table_headers(self) -> None:
        table = gen.build_table()
        self.assertIn("| Package | What it does | Type | Needs Python? | Source |", table)


class ReadmeFreshnessTest(unittest.TestCase):
    def test_readme_table_is_current(self) -> None:
        current = gen.README.read_text(encoding="utf-8")
        updated = gen.splice(current, gen.build_table())
        self.assertEqual(current, updated,
                         "README.md packages table is stale; run "
                         "`mise run generate-readme`")


if __name__ == "__main__":
    unittest.main()
