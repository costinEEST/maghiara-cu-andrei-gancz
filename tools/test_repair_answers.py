"""Recovered answers must be static, complete and derived from source data."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from bs4 import BeautifulSoup

import repair_answers

SOURCE = (
    r"I[0][1][0][0] = '\u0062\u0065\u0074\u0065\u0067'; "
    r"I[1][1][0][0] = '\u0073\u007A\u00ED\u0076';"
)
PAGE = """<div class="lesson-content"><span lang="hu">ő és ű</span>
<select id="Gap0" aria-label="Răspunsul 1"><option value=""></option>
<option lang="ro" value="beteg">beteg</option></select>
<input id="Gap1" aria-label="Răspunsul 2" type="text">
<details class="solutions"><summary>Vezi răspunsurile</summary><ol></ol>
</details></div>"""


class RepairTests(unittest.TestCase):
    def test_static_answers_and_grading_keys_exist_before_any_interaction(self):
        updated, count = repair_answers.repair_page(PAGE, SOURCE)
        doc = BeautifulSoup(updated, "html.parser")
        self.assertEqual(count, 2)
        self.assertEqual(
            [li.get_text() for li in doc.select(".solutions li")], ["beteg", "szív"]
        )
        self.assertTrue(
            all(li.get("lang") == "hu" for li in doc.select(".solutions li"))
        )
        field = doc.find(id="Gap1")
        assert field is not None
        answers = field.get("data-answers")
        assert isinstance(answers, str)
        self.assertEqual(json.loads(answers), ["szív"])
        self.assertIsNotNone(doc.select_one("[data-check]"))
        self.assertIsNotNone(doc.select_one("[data-reset]"))
        option = doc.select_one("option[value=beteg]")
        assert option is not None
        self.assertEqual(option["lang"], "hu")
        self.assertIn('<span lang="hu">ő és ű</span>', updated)

    def test_source_escapes_and_existing_options_confirm_legacy_typo(self):
        page = PAGE.replace('value="beteg">beteg', 'value="Szerelő">Szerelő')
        source = SOURCE.replace(r"\u0062\u0065\u0074\u0065\u0067", r"\u0053zerelu0151")
        updated, _ = repair_answers.repair_page(page, source)
        self.assertNotIn("u0151", updated)
        self.assertIn("Szerelő", updated)

    def test_verified_missing_option_and_alternative_are_selectable(self):
        source = SOURCE + " I[0][1][1][0] = 'betegek';"
        updated, _ = repair_answers.repair_page(PAGE, source)
        doc = BeautifulSoup(updated, "html.parser")
        field = doc.find(id="Gap0")
        assert field is not None
        answers = field.get("data-answers")
        assert isinstance(answers, str)
        self.assertEqual(json.loads(answers), ["beteg", "betegek"])
        self.assertIsNotNone(doc.select_one('option[value="betegek"]'))

    def test_literal_decoding_never_executes_javascript_and_escapes_html(self):
        source = SOURCE.replace(
            r"\u0073\u007A\u00ED\u0076", "<script>alert(1)</script>"
        )
        updated, _ = repair_answers.repair_page(PAGE, source)
        self.assertFalse(BeautifulSoup(updated, "html.parser").select("script"))
        self.assertEqual(repair_answers.decode_literal(r"'\u0151\u0171'"), "őű")
        self.assertEqual(
            repair_answers.source_text(b'<meta charset="iso-8859-1">\xe9'),
            '<meta charset="iso-8859-1">é',
        )

    def test_mismatched_keys_fail_before_any_pages_are_written(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "assets").mkdir()
            (root / "sources").mkdir()
            (root / "assets/inventory.json").write_text(
                json.dumps({"pages": [{"path": "a.html"}, {"path": "b.html"}]}),
                encoding="utf-8",
            )
            for name, source in [
                ("a.html", SOURCE),
                ("b.html", "I[9][1][0][0] = 'bad';"),
            ]:
                (root / name).write_text(PAGE, encoding="utf-8")
                (root / "sources" / name).write_text(source, encoding="utf-8")
            with self.assertRaises(ValueError):
                repair_answers.repair(root, root / "sources", write=True)
            self.assertEqual((root / "a.html").read_text(encoding="utf-8"), PAGE)


if __name__ == "__main__":
    unittest.main()
