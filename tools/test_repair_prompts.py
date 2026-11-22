"""Restore source-backed quiz context without guessing from answer keys."""

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import repair_prompts

ORIGINAL = """<html>
<head>
<script>key[0]="b";key[1]="a";</script>
</head>
<body>
<table>
<tr>
<td>Care este întrebarea potrivită?</td>
</tr>
</table>
<table>
<tr>
<td>1. \u2013 Eljössz?</td>
</tr>
<tr>
<td>
<input type="radio" onclick="answer[0]='a'">\u2013 Nem.</td>
<td>
<input type="radio" onclick="answer[0]='b'">\u2013 Igen.</td>
</tr>
<tr>
<td>2.</td>
<td>
<input type="radio" onclick="answer[1]='a'">\u2013 Jól vagy?</td>
<td>
<input type="radio" onclick="answer[1]='b'">\u2013 Mi bajod?</td>
</tr>
<tr>
<td>\u2013 Szomorú vagyok.</td>
</tr>
</table>
</body>
</html>"""
LOCAL = """<html lang="ro">
<head>
<title>Test</title>
</head>
<body>
<div class="lesson-content">Titlu Care este întrebarea potrivită?
<a href="https://example.org/">Usina Quiz</a>
<p>
<label for="one">\u2013 Nem.
<select id="one" data-answers="[&#34;\u2013 Igen.&#34;]">

<option value="">Alege răspunsul</option>

<option>\u2013 Nem.</option>

<option>\u2013 Igen.</option>
</select>
</label>
</p>
<p>
<label for="two">2.
<select id="two" data-answers="[&#34;\u2013 Jól vagy?&#34;]">

<option value="">Alege răspunsul</option>

<option>\u2013 Jól vagy?</option>

<option>\u2013 Mi bajod?</option>
</select>
</label>
</p>
<details class="solutions">
<ol>
<li>\u2013 Igen.</li>
<li>\u2013 Jól vagy?</li>
</ol>
</details>
</div>
</body>
</html>"""


class PromptTests(unittest.TestCase):
    def test_restores_both_question_and_given_response_with_language_labels(self):
        repaired, count = repair_prompts.repair_page(LOCAL, ORIGINAL)
        self.assertEqual(count, 2)
        before, after = (BeautifulSoup(s, "html.parser") for s in (LOCAL, repaired))
        self.assertEqual(
            [n["data-answers"] for n in before.select("select")],
            [n["data-answers"] for n in after.select("select")],
        )
        for identifier, prompt in [
            ("one", "\u2013 Eljössz?"),
            ("two", "\u2013 Szomorú vagyok."),
        ]:
            label = after.find("label", attrs={"for": identifier})
            assert label is not None
            passage = label.find("span", lang="hu")
            assert passage is not None
            self.assertEqual(passage.get_text(), prompt)
            self.assertIsNotNone(label.find("br"))
            self.assertEqual(label["lang"], "ro")
        self.assertIn('class="note" lang="ro"', repaired)
        self.assertEqual(repair_prompts.repair_page(repaired, ORIGINAL), (repaired, 0))

    def test_recovers_trailing_fragment_instead_of_copying_options(self):
        original = """<script>key[0]="b";</script>
<table>
<tr>
<td>
<input type="radio" onclick="answer[0]='a'">Az eredményed<br>
<input type="radio" onclick="answer[0]='b'">Az apád</td>
<td>aztán valaki!</td>
</tr>
</table>"""
        _, questions = repair_prompts.source_questions(original)
        self.assertEqual(questions[0]["prompt"], "… aztán valaki!")

    def test_html5_table_recovery_preserves_question_boundaries(self):
        original = """<script>key[0]="b";</script>
<table>
<tr>
<td colspan="3">1. Szükséged van …
<tr>
<td>
<input type="radio" onclick="answer[0]='a'">segítségre?
<td>
<input type="radio" onclick="answer[0]='b'">tanulságul?</table>"""
        _, questions = repair_prompts.source_questions(original)
        self.assertEqual(questions[0]["prompt"], "Szükséged van …")
        self.assertEqual(questions[0]["options"], ["segítségre?", "tanulságul?"])

    def test_corrects_corrupt_option_text_without_changing_correct_position(self):
        local = LOCAL.replace("Jól vagy?", "Jál vagy?")
        repaired, _ = repair_prompts.repair_page(local, ORIGINAL)
        doc = BeautifulSoup(repaired, "html.parser")
        field = doc.find("select", id="two")
        assert field is not None
        self.assertEqual(json.loads(str(field["data-answers"])), ["\u2013 Jól vagy?"])
        self.assertEqual(
            doc.select("details.solutions li")[1].get_text(), "\u2013 Jól vagy?"
        )
        with self.assertRaisesRegex(ValueError, "position disagrees"):
            repair_prompts.repair_page(
                LOCAL.replace("[&#34;\u2013 Igen.&#34;]", "[&#34;\u2013 Nem.&#34;]"),
                ORIGINAL,
            )

    def test_site_preflights_all_sources_before_writing(self):
        with TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            sources = Path(directory) / "original"
            (root / "assets").mkdir(parents=True)
            (root / "exercitii").mkdir()
            sources.mkdir()
            records = [
                {"path": f"exercitii/{name}.html", "group": "exercitii"}
                for name in ("a", "b")
            ]
            (root / "assets/inventory.json").write_text(json.dumps({"pages": records}))
            for name in ("a", "b"):
                (root / f"exercitii/{name}.html").write_text(LOCAL)
                (sources / f"{name}.html").write_text(ORIGINAL)
            (sources / "b.html").write_text(
                ORIGINAL.replace('key[0]="b"', 'key[0]="a"')
            )
            with self.assertRaisesRegex(ValueError, "position disagrees"):
                repair_prompts.repair_site(root, sources, write=True)
            self.assertEqual((root / "exercitii/a.html").read_text(), LOCAL)

    def test_source_decoding_and_import_safety(self):
        self.assertEqual(
            repair_prompts.decode_source("Kérem.".encode("cp1250")), "Kérem."
        )
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(repair_prompts)


if __name__ == "__main__":
    unittest.main()
