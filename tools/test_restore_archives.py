"""Restoring archives must preserve bytes and never publish failed downloads."""

import hashlib
import io
import json
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import restore_archives
from audit_archives import source_url


class RestoreTests(unittest.TestCase):
    def site(self, root):
        old = root / "assets/external/voc_imbrac_1.zip"
        old.parent.mkdir(parents=True)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("binary.bin", bytes(range(256)))
        raw = buffer.getvalue()
        old.write_bytes(raw)
        (root / "assets/inventory.json").write_text(
            json.dumps({"pages": []}), encoding="utf-8"
        )
        (root / "index.html").write_text(
            '<a href="assets/external/voc_imbrac_1.zip">Exercițiu</a>', encoding="utf-8"
        )
        return old, raw

    def test_downloads_preserve_binary_bytes_and_relocate_zip_links(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            old, raw = self.site(root)

            def download(url, path):
                path.write_bytes(raw)
                return {
                    "status": "valid",
                    "url": url,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }

            with patch("restore_archives.download_archive", side_effect=download):
                report = restore_archives.restore(root, root / "report.json")
            target = root / restore_archives.DESTINATION / old.name
            self.assertEqual(target.read_bytes(), raw)
            self.assertFalse(old.exists())
            self.assertIn(
                restore_archives.DESTINATION,
                (root / "index.html").read_text(encoding="utf-8"),
            )
            self.assertEqual(report["archives"][0]["local"]["status"], "valid")
            self.assertEqual(
                source_url(target.relative_to(root).as_posix()),
                report["archives"][0]["source_url"],
            )

    def test_failed_download_does_not_change_archives_or_pages(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            old, raw = self.site(root)
            before = (root / "index.html").read_bytes()
            with (
                patch(
                    "restore_archives.download_archive",
                    return_value={"status": "unverified"},
                ),
                self.assertRaises(ValueError),
            ):
                restore_archives.restore(root, root / "report.json")
            self.assertEqual(old.read_bytes(), raw)
            self.assertEqual((root / "index.html").read_bytes(), before)
            self.assertFalse((root / restore_archives.DESTINATION).exists())

    def test_download_note_is_removed_only_from_rewritten_links(self):
        source = (
            '<a href="https://example.test/a.rar">Játék</a><span lang="ro">\n'
            " (arhivă pe site-ul original;\n necesită internet)</span>"
            '<a href="https://elsewhere.test/">Other</a>'
        )
        result = restore_archives.localize_links(
            source, {"https://example.test/a.rar": "assets/a.rar"}
        )
        self.assertIn('href="assets/a.rar"', result)
        self.assertNotIn("necesită internet", result)
        self.assertIn('href="https://elsewhere.test/"', result)

    def test_missing_expected_link_prevents_rewrite(self):
        with self.assertRaises(ValueError):
            restore_archives.localize_links(
                "<p>No link</p>", {"missing.rar": "new.rar"}
            )


if __name__ == "__main__":
    unittest.main()
