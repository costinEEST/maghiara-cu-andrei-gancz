"""Preserve exercise content while removing layout-only table columns."""

import importlib
import json
import re
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import inline_cloze

FIELD = (
    '<input id="Gap0" type="text" lang="hu" aria-label="Spațiul 1" '
    'data-answers="[&#34;vallanom&#34;]">'
)


def page(table):
    return (
        '<html lang="ro"><body><div class="lesson-content">'
        + table
        + "</div></body></html>"
    )


def texts(source):
    return re.sub(r"\s+", "", BeautifulSoup(source, "html.parser").get_text())


class InlineClozeTests(unittest.TestCase):
    def test_dialogues_stack_without_losing_inline_words_or_keys(self):
        source = page(
            '<div class="table-scroll" aria-label="Dialoguri"><table><tr>'
            '<td>1.</td><td lang="hu">Be kell '
            + FIELD
            + " valamit.<br>Másik mondat.</td>"
            '<td>2.</td><td lang="hu">Másik párbeszéd.</td></tr></table></div>'
        )
        result, count, tables = inline_cloze.transform_page(source)
        self.assertEqual((count, tables), (1, 1))
        doc = BeautifulSoup(result, "html.parser")
        self.assertIsNone(doc.table)
        self.assertEqual(len(doc.select(".cloze-item")), 2)
        self.assertEqual(texts(source), texts(result))
        field = doc.find("input", id="Gap0")
        assert field is not None
        self.assertEqual(json.loads(str(field["data-answers"])), ["vallanom"])
        self.assertEqual(field["size"], "12")
        self.assertEqual(inline_cloze.transform_page(result), (result, 0, 0))

    def test_translation_and_conjugation_tables_remain_tables(self):
        tables = [
            '<table><tr><td lang="hu">A szó '
            + FIELD
            + '.</td><td lang="ro">Traducere.</td></tr></table>',
            "<table><tr><td>Mod</td><td>Timp</td><td>Persoană</td></tr>"
            "<tr><td>Indicativ</td><td>Prezent</td><td>" + FIELD + "</td></tr></table>",
        ]
        for table in tables:
            with self.subTest(table=table):
                result, _, flat = inline_cloze.transform_page(page(table))
                self.assertEqual(flat, 0)
                self.assertIsNotNone(BeautifulSoup(result, "html.parser").table)

    def test_speakers_become_inline_with_dialogue(self):
        source = page(
            '<table><tr><td>Péter:</td><td lang="hu">Szia!</td></tr>'
            '<tr><td>Zsuzsa:</td><td lang="hu">Jó napot!</td></tr></table>'
        )
        result, _, tables = inline_cloze.transform_page(source)
        self.assertEqual(tables, 1)
        self.assertEqual(texts(source), texts(result))
        self.assertEqual(
            len(BeautifulSoup(result, "html.parser").select(".cloze-line")), 2
        )

    def test_numbered_romanian_explanations_keep_their_language(self):
        source = page(
            "<table><tr><td>1</td><td>Explicație în română.</td></tr></table>"
        )
        result, _, _ = inline_cloze.transform_page(source)
        line = BeautifulSoup(result, "html.parser").select_one(".cloze-line")
        assert line is not None
        self.assertEqual(line["lang"], "ro")

    def test_dropdown_choices_and_stem_boundaries_are_preserved(self):
        control = FIELD.replace("<input", '<select data-cloze=""').replace(
            ">", '><option value="">Alege</option><option>vallanom</option></select>', 1
        )
        source = page(
            "<table><tr><td>1.</td><td>az" + control + "ban</td></tr></table>"
        )
        result, inputs, tables = inline_cloze.transform_page(source)
        self.assertEqual((inputs, tables), (0, 1))
        doc = BeautifulSoup(result, "html.parser")
        self.assertIsNotNone(doc.select_one("select[data-cloze]"))
        self.assertEqual(texts(source), texts(result))

    def test_fragment_loss_prevents_any_site_writes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "a.html"
            b = root / "b.html"
            a_source = page("<p>A szó " + FIELD + ".</p>")
            a.write_text(a_source, encoding="utf-8")
            b.write_text(
                page(
                    '<table><tr><td id="lost">1.</td><td>'
                    + FIELD
                    + "</td></tr></table>"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fragment IDs"):
                inline_cloze.transform_site(root, write=True)
            self.assertEqual(a.read_text(encoding="utf-8"), a_source)

    def test_import_does_not_read_site(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(inline_cloze)


if __name__ == "__main__":
    unittest.main()
