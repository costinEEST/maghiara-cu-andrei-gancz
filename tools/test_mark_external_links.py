"""Exercise external-link scope, privacy attributes and source preservation."""

import importlib
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup

import mark_external_links as links

BASE = "https://example.org/course/"


class ExternalLinkTests(unittest.TestCase):
    def test_scope_distinguishes_project_paths_and_other_schemes(self):
        for url in (
            "#section",
            "lesson.html",
            "../assets/file.rar",
            "mailto:a@example.org",
            "tel:123",
            "https://example.org/course/lesson.html",
            "https://example.org:443/course/",
        ):
            with self.subTest(url=url):
                self.assertFalse(links.is_external(url, BASE))
        for url in (
            "https://example.org/another-project/",
            "https://example.org/course-fake/",
            "https://example.org.evil.test/course/",
            "//outside.test/path",
            "http://example.org/course/",
        ):
            with self.subTest(url=url):
                self.assertTrue(links.is_external(url, BASE))

    def test_preserves_rel_tokens_markup_and_tab_behavior(self):
        source = (
            '<p>Țară <a href="https://outside.test/" rel="license">'
            '<span lang="hu">ő és ű</span></a> — text</p>'
        )
        marked = links.mark_html(source, BASE)
        doc = BeautifulSoup(marked, "html.parser")
        anchor = doc.a
        assert anchor is not None
        self.assertEqual(anchor["rel"], ["license", "noreferrer"])
        self.assertIsNone(anchor.get("target"))
        icon = anchor.select_one(".external-icon")
        description = anchor.select_one(".visually-hidden")
        assert icon is not None and description is not None
        self.assertEqual(icon["aria-hidden"], "true")
        self.assertEqual(description["lang"], "ro")
        self.assertIn('<span lang="hu">ő és ű</span>', marked)
        self.assertTrue(marked.endswith("</a> — text</p>"))
        self.assertEqual(links.mark_html(marked, BASE), marked)

    def test_ignores_script_comments_and_internal_links(self):
        source = """<!-- <a href="https://outside.test/">Example</a> -->
<script>const t = '<a href="https://outside.test/">Example</a>';</script>
<a href="lesson.html">Lecție</a><a href="file.zip">Arhivă</a>"""
        self.assertEqual(links.mark_html(source, BASE), source)

    def test_handles_greater_than_in_attributes_and_existing_blank_target(self):
        source = (
            '<a title="A > B" href="//outside.test/" '
            'target="_blank" rel="noopener">Link</a>'
        )
        marked = links.mark_html(source, BASE)
        anchor = BeautifulSoup(marked, "html.parser").a
        assert anchor is not None
        self.assertEqual(anchor["title"], "A > B")
        self.assertEqual(anchor["target"], "_blank")
        self.assertEqual(anchor["rel"], ["noopener", "noreferrer"])

    def test_import_has_no_file_side_effects(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(links)


if __name__ == "__main__":
    unittest.main()
