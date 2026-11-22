"""Archive audits must verify payloads and preserve working material."""

import hashlib
import importlib
import io
import json
import subprocess
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import audit_archives


class ArchiveTests(unittest.TestCase):
    def test_import_does_not_read_files_or_contact_sources(self):
        with (
            patch("pathlib.Path.read_text", side_effect=AssertionError("file read")),
            patch("pathlib.Path.read_bytes", side_effect=AssertionError("file read")),
            patch("urllib.request.urlopen", side_effect=AssertionError("network")),
        ):
            importlib.reload(audit_archives)
        # Reload again so imported aliases are not left bound to mocks.
        importlib.reload(audit_archives)

    def test_successful_http_response_must_contain_an_actual_archive(self):
        class Response(io.BytesIO):
            url = "https://www.nebulo.ro/example.rar"
            status = 200

        with patch(
            "audit_archives.urlopen", return_value=Response(b"<html>error</html>")
        ):
            result = audit_archives.remote_integrity(Response.url)
        self.assertEqual(result["http_status"], 200)
        self.assertEqual(result["status"], "broken")

    def test_zip_crc_and_invalid_payload(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "test.zip"
            with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("../never-extract.txt", "original payload")
            self.assertEqual(audit_archives.integrity(path)["status"], "valid")
            path.write_bytes(
                path.read_bytes().replace(b"original payload", b"modified payload")
            )
            self.assertEqual(audit_archives.integrity(path)["status"], "broken")
            path.write_bytes(b"<html>Not an archive</html>")
            self.assertEqual(audit_archives.integrity(path)["status"], "broken")
            self.assertFalse((Path(folder).parent / "never-extract.txt").exists())

    def test_rar_requires_supported_tool_and_actual_decompression(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "test.rar"
            path.write_bytes(b"Rar!\x1a\x07\x00payload")
            with patch("audit_archives.shutil.which", return_value=None):
                self.assertEqual(audit_archives.integrity(path)["status"], "unverified")
            for message, expected in [
                (b"Bad RAR file", "broken"),
                (b"Unsupported compression", "unverified"),
            ]:
                with (
                    patch("audit_archives.shutil.which", return_value="bsdtar"),
                    patch(
                        "audit_archives.subprocess.run",
                        return_value=subprocess.CompletedProcess([], 1, stderr=message),
                    ) as run,
                ):
                    self.assertEqual(audit_archives.integrity(path)["status"], expected)
                    self.assertIn("-xOf", run.call_args.args[0])
                    self.assertIs(run.call_args.kwargs["stdout"], subprocess.DEVNULL)

    def make_site(self, root):
        path = root / "assets/original/leckek/fajlok/test.rar"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"broken archive")
        (root / "assets/inventory.json").write_text(
            json.dumps(
                {
                    "pages": [
                        {
                            "path": "index.html",
                            "source_url": "https://www.nebulo.ro/lesson.html",
                        }
                    ]
                }
            )
        )
        (root / "index.html").write_text(
            '<p lang="hu"><a href="assets/original/leckek/fajlok/test.rar">Játék</a>'
            '<a href="assets/original/leckek/fajlok/test.rar">Again</a></p>',
            encoding="utf-8",
        )
        return path

    def test_replacement_rewrites_duplicate_links_then_removes_only_bad_copy(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = self.make_site(root)
            report = audit_archives.audit(root)
            self.assertEqual(len(report["archives"]), 1)
            record = report["archives"][0]
            self.assertEqual(
                record["source_url"], "https://www.nebulo.ro/leckek/fajlok/test.rar"
            )
            record["remote"] = {"status": "valid"}
            self.assertEqual(audit_archives.replace_broken(root, report), 1)
            self.assertFalse(path.exists())
            page = (root / "index.html").read_text(encoding="utf-8")
            self.assertEqual(
                page.count('href="https://www.nebulo.ro/leckek/fajlok/test.rar"'), 2
            )
            self.assertEqual(page.count('lang="ro"'), 2)
            again = audit_archives.audit(root)
            self.assertEqual(again["archives"][0]["local"]["status"], "absent")

    def test_unverified_remote_or_changed_copy_cannot_trigger_deletion(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            path = self.make_site(root)
            report = audit_archives.audit(root)
            before = (root / "index.html").read_bytes()
            with self.assertRaises(ValueError):
                audit_archives.replace_broken(root, report)
            self.assertTrue(path.exists())
            self.assertEqual(before, (root / "index.html").read_bytes())
            report["archives"][0]["remote"] = {"status": "valid"}
            path.write_bytes(b"different")
            self.assertNotEqual(
                hashlib.sha256(path.read_bytes()).hexdigest(),
                report["archives"][0]["local"]["sha256"],
            )
            with self.assertRaises(ValueError):
                audit_archives.replace_broken(root, report)
            self.assertTrue(path.exists())

    def test_symlink_escape_is_rejected(self):
        with TemporaryDirectory() as folder, TemporaryDirectory() as outside:
            root = Path(folder)
            self.make_site(root)
            target = Path(outside) / "outside.zip"
            target.write_bytes(b"never touch")
            (root / "escape.zip").symlink_to(target)
            with self.assertRaises(ValueError):
                audit_archives.audit(root)
            self.assertEqual(target.read_bytes(), b"never touch")


if __name__ == "__main__":
    unittest.main()
