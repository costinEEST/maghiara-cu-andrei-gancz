#!/usr/bin/env python3
"""Download verified originals into fajlok and point archive links to local files.

No archive is extracted into the website. All downloads must pass integrity
checks before any maintained files change. The report retains source URLs.
"""

import argparse
import hashlib
import html
import json
import os
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from audit_archives import HREF, SUFFIXES, audit, download_archive

DESTINATION = "assets/original/leckek/fajlok"
NOTE = (
    r'<span\s+lang="ro">\s*\(arhivă pe site-ul original;'
    r"\s*necesită internet\)</span\s*>"
)
LINK = re.compile(r"<a\b[^>]*>.*?</a\s*>(?:\s*" + NOTE + r")?", re.I | re.S)


def localize_links(source: str, replacements: dict[str, str]) -> str:
    seen: set[str] = set()

    def update(match: re.Match[str]) -> str:
        anchor = match.group()
        attr = HREF.search(anchor)
        if attr is None:
            return anchor
        old = html.unescape(attr[2])
        if old not in replacements:
            return anchor
        seen.add(old)
        anchor = (
            anchor[: attr.start(2)]
            + html.escape(replacements[old], quote=True)
            + anchor[attr.end(2) :]
        )
        return re.sub(NOTE, "", anchor, flags=re.I)

    result = LINK.sub(update, source)
    if seen != replacements.keys():
        raise ValueError("Page links changed since preflight")
    return result


def restore(root: Path, report_path: Path) -> dict[str, Any]:
    root = root.resolve()
    current = audit(root)
    records = current["archives"]
    destination = (root / DESTINATION).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Archive directory is outside the project")
    targets: dict[str, Path] = {}
    changes: dict[Path, dict[str, str]] = {}
    for record in records:
        url = record["source_url"]
        if not url or urlsplit(url).scheme != "https":
            raise ValueError(f"Missing HTTPS source: {record['path']}")
        name = Path(unquote(urlsplit(url).path)).name
        if Path(name).suffix.lower() not in SUFFIXES:
            raise ValueError(f"Invalid archive name: {name}")
        target = destination / name
        if target.is_symlink() or not target.resolve().is_relative_to(root):
            raise ValueError(f"Unsafe archive target: {target}")
        if target in targets.values() and url not in targets:
            raise ValueError(f"Conflicting archive names: {name}")
        targets[url] = target
        for ref in record["references"]:
            page = (root / ref["page"]).resolve()
            if not page.is_relative_to(root):
                raise ValueError("Page outside project")
            changes.setdefault(page, {})[ref["href"]] = Path(
                os.path.relpath(target, page.parent)
            ).as_posix()
    # Preflight every HTML edit before downloading or replacing files.
    pages = {
        page: localize_links(page.read_text(encoding="utf-8"), links)
        for page, links in changes.items()
    }
    with tempfile.TemporaryDirectory(prefix="nebulo-restore-") as folder:
        staging = Path(folder)
        urls = sorted(targets)
        paths = [staging / targets[url].name for url in urls]
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(download_archive, urls, paths))
        downloads = dict(zip(urls, results, strict=True))
        report_path.write_text(
            json.dumps({"downloads": downloads}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if any(result["status"] != "valid" for result in results):
            raise ValueError(
                "Some archives failed verification; site unchanged. See report."
            )
        destination.mkdir(parents=True, exist_ok=True)
        for url, staged in zip(urls, paths, strict=True):
            # Copy as binary and publish atomically; never decode/re-encode archives.
            with tempfile.NamedTemporaryFile(
                dir=destination, suffix=".part", delete=False
            ) as output:
                temporary = Path(output.name)
            try:
                shutil.copyfile(staged, temporary)
                if (
                    hashlib.sha256(temporary.read_bytes()).hexdigest()
                    != downloads[url]["sha256"]
                ):
                    raise ValueError("Copy checksum mismatch")
                temporary.replace(targets[url])
            finally:
                temporary.unlink(missing_ok=True)
        for page, content in pages.items():
            page.write_text(content, encoding="utf-8")
        for record in records:
            old = record["path"]
            if old and (root / old) != targets[record["source_url"]]:
                (root / old).unlink()
        final = audit(root)
        for record in final["archives"]:
            record["remote"] = downloads[record["source_url"]]
            record["action"] = "downloaded_verified_original; linked_local_archive"
        report_path.write_text(
            json.dumps(final, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = restore(args.root, args.report)
    print(f"Restored and verified {len(report['archives'])} local archives.")


if __name__ == "__main__":
    main()
