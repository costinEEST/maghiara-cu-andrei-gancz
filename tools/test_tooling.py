"""Exercise maintenance tools on temporary sites, never the real lesson files."""

import importlib
import json
import shutil
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import label_languages
import prepare_seo
import validate

PROJECT = Path(__file__).resolve().parents[1]


def make_site(root, extra=None):
    pages = {
        "index.html": ("Cuprins", ""),
        "referinte/despre-editie.html": ("Despre ediție", ""),
    }
    records = []
    for relative, heading in (extra or {}).items():
        pages[relative] = (heading, "")
        records.append({"path": relative, "old": relative, "group": "gramatica"})
    config = {
        "public_url": "https://example.org/course/",
        "site_name": "Test course",
        "locale": "ro_RO",
        "social_image": "assets/social/site.png",
    }
    for relative, data in {
        "assets/inventory.json": {"pages": records, "issues": []},
        "site-config.json": config,
    }.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    for relative, (heading, body) in pages.items():
        links = ""
        if relative == "index.html":
            links = "".join(
                f'<a href="{target}">Pagina</a>'
                for target in pages
                if target != relative
            )
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '<!doctype html><html lang="ro"><head><meta name="viewport" '
            'content="width=device-width"><title>Original</title></head>'
            f"<body><main><h1>{heading}</h1>{body}{links}</main></body></html>",
            encoding="utf-8",
        )
    image = root / config["social_image"]
    image.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PROJECT / "assets/social/site.png", image)
    shutil.copyfile(PROJECT / "assets/favicon.svg", root / "assets/favicon.svg")


class MaintenanceTests(unittest.TestCase):
    def test_importing_tools_does_not_read_or_rewrite_site_files(self):
        with (
            patch.object(Path, "read_text", side_effect=AssertionError("Import read")),
            patch.object(
                Path, "write_text", side_effect=AssertionError("Import write")
            ),
        ):
            for module in (label_languages, prepare_seo, validate):
                importlib.reload(module)

    def test_generated_metadata_passes_the_site_validator(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root)
            self.assertEqual(prepare_seo.prepare_seo(root), 2)
            report = validate.validate_site(root)
            self.assertEqual(report["errors"], [])

    def test_table_regions_accept_visible_captions_and_reject_broken_labels(self):
        cases = (
            ('aria-labelledby="caption"', "0", "Specificații", True),
            ('aria-label="Specificații"', "0", "", True),
            ('aria-labelledby="missing"', "0", "Specificații", False),
            ('aria-labelledby="caption"', "0", "", False),
            ('aria-label="  "', "0", "", False),
            ('aria-labelledby="caption"', "-1", "Specificații", False),
        )
        for label, tabindex, caption, valid in cases:
            with (
                self.subTest(label=label, caption=caption),
                TemporaryDirectory() as folder,
            ):
                root = Path(folder)
                make_site(root)
                path = root / "index.html"
                source = path.read_text(encoding="utf-8")
                markup = (
                    f'<div class="table-scroll" role="region" tabindex="{tabindex}" '
                    f'{label}><table><caption id="caption">{caption}</caption>'
                    '<tr><th scope="row">Lățime</th><td>40 cm</td></tr></table></div>'
                )
                path.write_text(
                    source.replace("</main>", markup + "</main>"), encoding="utf-8"
                )
                prepare_seo.prepare_seo(root)
                errors = validate.validate_site(root)["errors"]
                self.assertEqual(not errors, valid, errors)

    def test_duplicate_metadata_does_not_partially_rewrite_pages(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(
                root, {"gramatica/a.html": "Armonie", "gramatica/b.html": "Armonie"}
            )
            before = {path: path.read_bytes() for path in root.rglob("*.html")}
            with self.assertRaisesRegex(ValueError, "Duplicate titles"):
                prepare_seo.prepare_seo(root)
            self.assertEqual(before, {path: path.read_bytes() for path in before})
            self.assertFalse((root / "sitemap.xml").exists())

    def test_seo_preserves_body_and_uses_catalog_and_padded_lesson_numbers(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root, {"andras/two.html": "Doi", "exercitii/a.html": "Test"})
            inventory_path = root / "assets/inventory.json"
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            lesson, activity = inventory["pages"]
            lesson.update(group="andras", number=2)
            activity.update(
                group="exercitii", catalog_number=10, title="Lecția 002, exercițiul 001"
            )
            inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
            path = root / "andras/two.html"
            original = path.read_text(encoding="utf-8")
            body = original[original.index("<body>") :]
            prepare_seo.prepare_seo(root)
            actual = path.read_text(encoding="utf-8")
            self.assertEqual(actual[actual.index("<body>") :], body)
            self.assertIn("Lecția 002:", actual)
            self.assertIn(
                "Activitatea 010 — Lecția 002, exercițiul 001",
                (root / "exercitii/a.html").read_text(encoding="utf-8"),
            )

    def test_malformed_page_schema_answers_and_png_are_reported(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root)
            prepare_seo.prepare_seo(root)
            path = root / "referinte/despre-editie.html"
            doc = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            og_url = doc.select_one('meta[property="og:url"]')
            schema = doc.select_one("script[data-site-schema]")
            main = doc.main
            assert og_url is not None and schema is not None and main is not None
            og_url.decompose()
            schema.string = '{"@graph": []}'
            control = doc.new_tag("input", attrs={"data-answers": "[12]"})
            main.append(control)
            path.write_text(str(doc), encoding="utf-8")
            (root / "assets/social/site.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            errors = "\n".join(validate.validate_site(root)["errors"])
            for expected in (
                "Missing Open Graph url",
                "Invalid JSON-LD graph",
                "invalid answer key",
                "1200x630 PNG",
                "Unlabelled control",
            ):
                self.assertIn(expected, errors)

    def test_missing_page_and_invalid_inventory_are_reported(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root)
            (root / "index.html").unlink()
            self.assertTrue(validate.validate_site(root)["errors"])
            path = root / "assets/inventory.json"
            path.write_text("{bad json", encoding="utf-8")
            self.assertIn(
                "Cannot load site inputs", validate.validate_site(root)["errors"][0]
            )

    def test_empty_solutions_and_ungraded_cloze_fields_are_reported(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root)
            path = root / "index.html"
            source = path.read_text(encoding="utf-8")
            broken = (
                '<div class="lesson-content"><select id="Gap0" aria-label="Răspuns">'
                '<option value="beteg">beteg</option></select>'
                '<details class="solutions"><summary>Vezi răspunsurile</summary>'
                "<ol></ol></details></div>"
            )
            path.write_text(
                source.replace("</main>", broken + "</main>"), encoding="utf-8"
            )
            prepare_seo.prepare_seo(root)
            errors = "\n".join(validate.validate_site(root)["errors"])
            self.assertIn("Empty solutions disclosure", errors)
            self.assertIn("Missing cloze answer key", errors)

    def test_language_markup_keeps_text_and_comments(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            make_site(root)
            path = root / "index.html"
            doc = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            main = doc.main
            assert main is not None
            content = BeautifulSoup(
                '<div class="lesson-content"><p>hogy vagy?</p>'
                "<p>O explicație în română.</p><!-- ő: keep this comment --></div>",
                "html.parser",
            )
            main.append(content)
            before = main.get_text()
            path.write_text(str(doc), encoding="utf-8")
            label_languages.label_languages(root)
            updated = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
            updated_main = updated.main
            first_paragraph = updated.select_one(".lesson-content p")
            assert updated_main is not None and first_paragraph is not None
            self.assertEqual(before, updated_main.get_text())
            self.assertEqual(first_paragraph["lang"], "hu")
            self.assertNotIn("lang", updated.select(".lesson-content p")[1].attrs)
            self.assertIn("<!-- ő: keep this comment -->", str(updated))

    def test_invalid_language_inputs_do_not_partially_rewrite_pages(self):
        for malformed in (
            '<html><body><input data-answers="[12]"></body></html>',
            '<html><body><input data-answers="{}"></body></html>',
            "<p>A document without an html element.</p>",
        ):
            with self.subTest(source=malformed), TemporaryDirectory() as folder:
                root = Path(folder)
                make_site(root)
                (root / "referinte/despre-editie.html").write_text(
                    malformed, encoding="utf-8"
                )
                before = {path: path.read_bytes() for path in root.rglob("*.html")}
                with self.assertRaises(ValueError):
                    label_languages.label_languages(root)
                self.assertEqual(before, {path: path.read_bytes() for path in before})


if __name__ == "__main__":
    unittest.main()
