"""Regression checks for recursive crawling and legacy URL edge cases."""

import unittest
from email.message import Message
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from check_links import Document, crawl, external_status


class LinkCheckerTests(unittest.TestCase):
    def test_parser_override_accepts_base_class_keyword_arguments(self):
        document = Document("")
        document.handle_starttag(tag="a", attrs=[("href", "lesson.html")])
        self.assertEqual(document.refs, [("lesson.html", 1)])

    def test_missing_entry_is_not_counted_as_a_checked_page(self):
        with TemporaryDirectory() as folder:
            report = crawl(Path(folder) / "index.html")
            self.assertEqual(report["html_pages"], 0)
            self.assertEqual(len(report["broken"]), 1)

    def test_crawls_and_checks_fragments_and_encoded_paths(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text(
                '<a href="lesson.html#ok">Lesson</a><img src="a%20b.png">'
                '<a href="lesson.html#missing">Bad</a>',
                encoding="utf-8",
            )
            (root / "lesson.html").write_text(
                '<h1 id="ok">Lesson</h1><a href="index.html">Index</a>',
                encoding="utf-8",
            )
            (root / "a b.png").write_bytes(b"fixture")
            report = crawl(root / "index.html")
            self.assertEqual(report["html_pages"], 2)
            self.assertEqual(len(report["broken"]), 1)
            self.assertEqual(report["broken"][0]["reason"], "Missing fragment #missing")

    def test_malformed_external_url_and_escape_are_reported_offline(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text(
                '<a href="https://example.com/a&lt;/a&gt;">Bad</a>'
                '<a href="../private.html">Escape</a>',
                encoding="utf-8",
            )
            self.assertEqual(len(crawl(root / "index.html")["broken"]), 2)

    def test_external_unicode_url_keeps_original_report_key(self):
        class Response:
            status = 200
            url = "https://example.org/caf%C3%A9"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        with patch("check_links.urlopen", return_value=Response()):
            self.assertEqual(
                external_status("https://example.org/café", 2)[0],
                "https://example.org/café",
            )

    def test_invalid_url_is_reported_without_aborting_the_crawl(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text(
                '<a href="http://[broken">Bad IPv6</a>'
                '<a href="https:///missing-host">Bad host</a>',
                encoding="utf-8",
            )
            report = crawl(root / "index.html")
            self.assertEqual(len(report["broken"]), 2)
            self.assertIn("Malformed URL", report["broken"][0]["reason"])

    def test_data_url_in_srcset_is_not_crawled_as_a_local_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "index.html").write_text(
                '<img srcset="data:image/png;base64,AAAA 1x, image.png 2x">',
                encoding="utf-8",
            )
            (root / "image.png").write_bytes(b"fixture")
            self.assertEqual(crawl(root / "index.html")["broken"], [])

    def test_directory_index_symlink_cannot_escape_site(self):
        with TemporaryDirectory() as folder:
            base = Path(folder)
            root = base / "site"
            root.mkdir()
            (root / "subdir").mkdir()
            (base / "outside.html").write_text("Private", encoding="utf-8")
            try:
                (root / "subdir/index.html").symlink_to(base / "outside.html")
            except OSError as error:
                self.skipTest(str(error))
            (root / "index.html").write_text(
                '<a href="subdir/">Escape</a>', encoding="utf-8"
            )
            report = crawl(root / "index.html")
            self.assertEqual(len(report["broken"]), 1)
            self.assertEqual(report["html_pages"], 1)

    def test_external_failures_keep_distinct_outcomes(self):
        for code, expected in [(404, "broken"), (410, "broken"), (403, "unverified")]:
            with (
                self.subTest(code=code),
                patch(
                    "check_links.urlopen",
                    side_effect=HTTPError(
                        "https://example.org/", code, "error", Message(), None
                    ),
                ) as request,
            ):
                self.assertEqual(
                    external_status("https://example.org/", 1)[2], expected
                )
                self.assertEqual(request.call_count, 2)
                self.assertEqual(request.call_args[0][0].get_method(), "GET")
        with patch("check_links.urlopen", side_effect=URLError("timeout")):
            self.assertEqual(
                external_status("https://example.org/", 1)[2], "unverified"
            )


if __name__ == "__main__":
    unittest.main()
