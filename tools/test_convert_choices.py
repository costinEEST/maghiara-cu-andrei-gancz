"""Test semantic conversion while retaining answers, language and task type."""

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import convert_choices
import repair_prompts
from test_repair_prompts import LOCAL as SOURCE_LOCAL
from test_repair_prompts import ORIGINAL

LOCAL = SOURCE_LOCAL.replace(
    "</body>", '<button data-check="" type="button">Verifică</button></body>'
)


class ChoiceTests(unittest.TestCase):
    def test_radio_groups_preserve_keys_prompts_and_start_unanswered(self):
        source, _ = repair_prompts.repair_page(LOCAL, ORIGINAL)
        converted, count = convert_choices.convert_page(source)
        self.assertEqual(count, 2)
        before, after = (BeautifulSoup(s, "html.parser") for s in (source, converted))
        groups = after.select("fieldset[data-choice]")
        self.assertEqual(
            [s["data-answers"] for s in before.select("select")],
            [g["data-answers"] for g in groups],
        )
        names = []
        for group in groups:
            radios = group.select("input[type=radio]")
            self.assertFalse(any(r.has_attr("checked") for r in radios))
            self.assertEqual(len({r["name"] for r in radios}), 1)
            names.append(radios[0]["name"])
            passage = group.select_one("legend span[lang=hu]")
            assert passage is not None
            self.assertTrue(passage.get_text())
            for radio in radios:
                self.assertIsNotNone(after.find("label", attrs={"for": radio["id"]}))
        self.assertEqual(len(set(names)), 2)
        self.assertEqual(convert_choices.convert_page(converted), (converted, 0))
        self.assertEqual(
            repair_prompts.repair_page(converted, ORIGINAL), (converted, 0)
        )

    def test_matching_and_cloze_tasks_are_unchanged(self):
        matching = LOCAL.replace(
            "Titlu Care", '<p class="note">Asociază fiecare element</p>Care'
        )
        self.assertEqual(convert_choices.convert_page(matching), (matching, 0))
        cloze = LOCAL.replace("<select ", '<select data-cloze="" ')
        self.assertEqual(convert_choices.convert_page(cloze), (cloze, 0))

    def test_preserves_multiple_accepted_alternatives_for_one_selection(self):
        source = LOCAL.replace(
            "[&#34;\u2013 Igen.&#34;]", "[&#34;\u2013 Igen.&#34;,&#34;\u2013 Nem.&#34;]"
        )
        result, count = convert_choices.convert_page(source)
        self.assertEqual(count, 2)
        group = BeautifulSoup(result, "html.parser").select_one("fieldset[data-choice]")
        assert group is not None
        self.assertEqual(len(json.loads(str(group["data-answers"]))), 2)
        multiple = source.replace("<select ", '<select multiple="" ')
        self.assertEqual(convert_choices.convert_page(multiple), (multiple, 0))

    def test_option_whitespace_matches_browser_values_and_preserves_language(self):
        source = LOCAL.replace(">\u2013 Igen.</option>", ">\n  \u2013 Igen.\n</option>")
        source = source.replace("<option>", '<option lang="ro">')
        result, _ = convert_choices.convert_page(source)
        doc = BeautifulSoup(result, "html.parser")
        radio = doc.select_one('input[value="\u2013 Igen."]')
        assert radio is not None
        label = radio.find_parent("label")
        assert label is not None
        self.assertIsNotNone(label.select_one('[lang="ro"]'))

    def test_invalid_later_page_prevents_partial_writes(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            a = root / "a.html"
            b = root / "b.html"
            a.write_text(LOCAL, encoding="utf-8")
            b.write_text(
                LOCAL.replace("[&#34;\u2013 Igen.&#34;]", "invalid"), encoding="utf-8"
            )
            with self.assertRaises(ValueError):
                convert_choices.convert_site(root, write=True)
            self.assertEqual(a.read_text(encoding="utf-8"), LOCAL)

    def test_bilingual_answers_keep_their_value_and_split_language_labels(self):
        source = LOCAL.replace("\u2013 Igen.", "Igaz — adevărat").replace(
            "\u2013 Nem.", "Hamis — fals"
        )
        result, _ = convert_choices.convert_page(source)
        doc = BeautifulSoup(result, "html.parser")
        radio = doc.select_one('input[value="Igaz — adevărat"]')
        assert radio is not None
        label = radio.find_parent("label")
        assert label is not None
        hu = label.select_one("[lang=hu]")
        ro = label.select_one("[lang=ro]")
        assert hu is not None and ro is not None
        self.assertEqual(hu.get_text(), "Igaz")
        self.assertEqual(ro.get_text(), " — adevărat")
        group = radio.find_parent("fieldset")
        assert group is not None
        self.assertEqual(json.loads(str(group["data-answers"])), ["Igaz — adevărat"])

    def test_import_has_no_file_side_effects(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(convert_choices)


if __name__ == "__main__":
    unittest.main()
