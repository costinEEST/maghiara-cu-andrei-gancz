"""Protect decoded answer data and text while enforcing quote conventions."""

import importlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from bs4 import BeautifulSoup

import html_attributes


class AttributeTests(unittest.TestCase):
    def test_normalization_preserves_json_and_ignores_script_and_comments(self):
        source = """<!doctype html><html lang="ro"><head><title>Test</title></head>
<body><!-- <input data-answers='["fals"]'> -->
<script>const text = `<input data-answers='["fals"]'>`;</script>
<p lang='hu'>árvíztűrő tükörfúrógép &amp; șț</p>
<input
 data-answers='["&lt;b&gt;Reggel&lt;/b&gt;", "ő &amp; ű", "&amp;quot;"]'/>
<a title='O &quot;carte&quot;' href="a.html">Citește</a></body></html>"""
        result = html_attributes.normalize_quotes(source)
        before = BeautifulSoup(source, "html.parser")
        after = BeautifulSoup(result, "html.parser")
        self.assertEqual(before.decode(), after.decode())
        field = after.select_one("[data-answers]")
        assert field is not None
        self.assertEqual(
            json.loads(str(field["data-answers"])), ["<b>Reggel</b>", "ő & ű", "&quot;"]
        )
        self.assertIn('data-answers="[&#34;', result)
        self.assertIn("<!-- <input data-answers='[\"fals\"]'> -->", result)
        self.assertIn("const text = `<input data-answers='[\"fals\"]'>`;", result)
        self.assertEqual(html_attributes.normalize_quotes(result), result)

    def test_serializer_always_uses_double_quotes_and_round_trips_answers(self):
        doc = BeautifulSoup('<p lang="hu">ő és ű</p><input>', "html.parser")
        field = doc.input
        assert field is not None
        answers = ['"idézet"', "Bob's", "<b>ő & ű</b>", "&quot;"]
        field["data-answers"] = json.dumps(answers, ensure_ascii=False)
        result = html_attributes.serialize_html(doc)
        self.assertIn('data-answers="[&#34;', result)
        reparsed = BeautifulSoup(result, "html.parser").input
        assert reparsed is not None
        self.assertEqual(json.loads(str(reparsed["data-answers"])), answers)
        self.assertEqual(doc.decode(), BeautifulSoup(result, "html.parser").decode())

    def test_default_audit_does_not_write_and_write_preflights_every_file(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "good.html"
            original = "<input data-answers='[\"ő\"]'>"
            path.write_text(original, encoding="utf-8")
            self.assertEqual(html_attributes.normalize_site(root), ["good.html"])
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            (root / "invalid.html").write_bytes(b"\xff")
            with self.assertRaises(UnicodeError):
                html_attributes.normalize_site(root, write=True)
            self.assertEqual(path.read_text(encoding="utf-8"), original)
            (root / "invalid.html").unlink()
            html_attributes.normalize_site(root, write=True)
            self.assertEqual(html_attributes.normalize_site(root), [])

    def test_import_has_no_file_side_effects(self):
        with patch.object(Path, "read_text", side_effect=AssertionError("read")):
            importlib.reload(html_attributes)


if __name__ == "__main__":
    unittest.main()
