"""Regression tests for encoding repair and pedagogical catalog ordering."""

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import index_catalog


class CatalogTests(unittest.TestCase):
    def test_repairs_mojibake_without_changing_hungarian(self):
        self.assertEqual(
            index_catalog.repair_encoding("PlÄƒcere â€“ neplÄƒcere"),
            "Plăcere \u2013 neplăcere",
        )
        self.assertEqual(
            index_catalog.repair_encoding("keresztrejtvÃ©ny szÃ³"),
            "keresztrejtvény szó",
        )
        valid = "árvíztűrő tükörfúrógép; șțâîă"
        self.assertEqual(index_catalog.repair_encoding(valid), valid)
        self.assertEqual(
            index_catalog.repair_encoding("Mi�rt megnős�ltem"), "Miért megnősültem"
        )

    def test_padding_never_changes_paths_or_years(self):
        self.assertEqual(
            index_catalog.pad_numbers("Lecția 2, exercițiul 10 /lectia-2.html 2026"),
            "Lecția 002, exercițiul 010 /lectia-2.html 2026",
        )
        self.assertEqual(index_catalog.pad_numbers("Lecția\n 002"), "Lecția\n 002")

    def test_row_comparison_ignores_formatter_wrapping(self):
        plain = BeautifulSoup(
            '<li><a href="a.html"><span>Două cuvinte</span></a></li>', "html.parser"
        ).li
        wrapped = BeautifulSoup(
            '<li>\n<a href="a.html"><span>Două\n  cuvinte</span></a>\n</li>',
            "html.parser",
        ).li
        self.assertEqual(
            index_catalog.row_signature(plain), index_catalog.row_signature(wrapped)
        )

    def test_import_does_not_touch_files(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(index_catalog)

    def make_site(self, root):
        pages = [
            {
                "path": "andras/ten.html",
                "group": "andras",
                "number": 10,
                "title": "Zece",
            },
            {"path": "andras/two.html", "group": "andras", "number": 2, "title": "Doi"},
            {
                "path": "exercitii/a.html",
                "group": "exercitii",
                "number": None,
                "title": "Lecția 1, exercițiul 1",
            },
            {
                "path": "exercitii/b.html",
                "group": "exercitii",
                "number": None,
                "title": "PlÄƒcere â€“ neplÄƒcere 1",
            },
        ]
        bodies = {
            "index.html": (
                '<section id="activitati"><ol class="catalog-list"></ol></section>'
            ),
            "referinte/despre-editie.html": "",
            "andras/two.html": '<a href="../exercitii/a.html">Exercițiu</a>',
            "andras/ten.html": '<a href="../exercitii/b.html">Exercițiu</a>'
            '<a href="../exercitii/a.html">Comun</a>',
            "exercitii/a.html": '<span lang="hu">tűrő</span>',
            "exercitii/b.html": "",
        }
        for relative, body in bodies.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "<html><head><title>Test</title></head><body><h1>Test</h1>"
                f'<div class="lesson-content">{body}</div></body></html>',
                encoding="utf-8",
            )
        (root / "assets").mkdir()
        (root / "assets/inventory.json").write_text(
            json.dumps({"pages": pages}), encoding="utf-8"
        )

    def test_numeric_order_shared_parents_and_idempotence(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_site(root)
            result = index_catalog.index_catalog(root, write=True)
            self.assertEqual(result["shared"], 1)
            records = json.loads((root / "assets/inventory.json").read_text())["pages"]
            self.assertEqual(records[2]["catalog_number"], 1)
            self.assertEqual(records[3]["catalog_number"], 2)
            self.assertEqual(records[2]["title"], "Lecția 002, exercițiul 001")
            self.assertEqual(len(records[2]["parents"]), 2)
            self.assertEqual(records[2]["source_title"], "Lecția 001, exercițiul 001")
            self.assertIn(
                '<span lang="hu">tűrő</span>', (root / "exercitii/a.html").read_text()
            )
            second = index_catalog.index_catalog(root)
            self.assertEqual(second["changed"], [])
            self.assertFalse(second["inventory_changed"])

    def test_orphan_aborts_before_writes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_site(root)
            path = root / "andras/ten.html"
            path.write_text(path.read_text().replace("../exercitii/b.html", "#missing"))
            before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
            with self.assertRaisesRegex(ValueError, "without a parent"):
                index_catalog.index_catalog(root, write=True)
            self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == "__main__":
    unittest.main()
