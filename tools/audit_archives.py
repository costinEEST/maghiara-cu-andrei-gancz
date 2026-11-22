#!/usr/bin/env python3
"""Test local/downloaded archives without extracting files into the site.

Default: read-only local audit. --check-remote downloads to an automatically
removed temporary directory. --replace-broken rewrites verified links before
removing corrupt copies; it never replaces a valid local archive.
"""

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import tempfile
import time
import zipfile
import zlib
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.client import HTTPException
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

SUFFIXES = {".rar", ".zip", ".7z", ".tar", ".gz"}
OFFICIAL = "https://www.nebulo.ro/"
SPECIAL_SOURCES = {
    "assets/original/leckek/fajlok/voc_imbrac_1.zip": "https://static.blog4ever.com/2010/10/444844/voc_imbrac_1.zip",
    "assets/external/voc_imbrac_1.zip": "https://static.blog4ever.com/2010/10/444844/voc_imbrac_1.zip",
}
ANCHOR = re.compile(r"<a\b[^>]*>.*?</a\s*>", re.I | re.S)
HREF = re.compile(r"\bhref\s*=\s*([\"'])(.*?)\1", re.I | re.S)


def integrity(path: Path) -> dict[str, str]:
    """Read/decompress all entries, but never extract them onto the filesystem."""
    if path.suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(path) as archive:
                if sum(item.file_size for item in archive.infolist()) > 128_000_000:
                    return {
                        "status": "unverified",
                        "detail": "Expanded size exceeds 128 MB",
                    }
                bad = archive.testzip()
                return {
                    "status": "broken" if bad else "valid",
                    "detail": f"CRC error: {bad}"
                    if bad
                    else f"{len(archive.infolist())} entries; CRC verified",
                }
        except (zipfile.BadZipFile, EOFError, zlib.error) as error:
            return {"status": "broken", "detail": str(error)}
        except (RuntimeError, NotImplementedError, OSError) as error:
            return {"status": "unverified", "detail": str(error)}
    if path.suffix.lower() == ".rar":
        try:
            with path.open("rb") as source:
                if not source.read(8).startswith(b"Rar!\x1a\x07"):
                    return {"status": "broken", "detail": "Invalid RAR signature"}
        except OSError as error:
            return {"status": "unverified", "detail": str(error)}
    executable = shutil.which("bsdtar")
    if not executable:
        return {
            "status": "unverified",
            "detail": "Install bsdtar (libarchive) to verify this format",
        }
    try:
        result = subprocess.run(
            [executable, "-xOf", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            timeout=45,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        return {"status": "unverified", "detail": str(error)}
    detail = result.stderr.decode("utf-8", errors="replace").strip()
    if result.returncode == 0:
        return {"status": "valid", "detail": "All entries decompressed successfully"}
    unsupported = any(
        word in detail.lower()
        for word in (
            "unsupported",
            "not supported",
            "passphrase",
            "encrypted",
            "unrecognized archive format",
        )
    )
    return {
        "status": "unverified" if unsupported else "broken",
        "detail": detail[:1000],
    }


def source_url(relative: str) -> str | None:
    if relative in SPECIAL_SOURCES:
        return SPECIAL_SOURCES[relative]
    if relative.startswith("assets/original/"):
        return urljoin(OFFICIAL, relative.removeprefix("assets/original/"))
    return SPECIAL_SOURCES.get(relative)


def references(root: Path) -> dict[str, list[dict[str, str]]]:
    inventory = json.loads((root / "assets/inventory.json").read_text(encoding="utf-8"))
    sources = {page["path"]: page["source_url"] for page in inventory["pages"]}
    found: dict[str, list[dict[str, str]]] = {}
    for page in sorted(root.rglob("*.html")):
        if not page.resolve().is_relative_to(root):
            raise ValueError(f"Page outside project: {page}")
        relative = page.relative_to(root).as_posix()
        for anchor in ANCHOR.finditer(page.read_text(encoding="utf-8")):
            match = HREF.search(anchor.group())
            if not match:
                continue
            href = html.unescape(match[2])
            parsed = urlsplit(href)
            if Path(parsed.path).suffix.lower() not in SUFFIXES:
                continue
            if parsed.scheme or parsed.netloc:
                key = href
            else:
                target = (page.parent / unquote(parsed.path)).resolve()
                if not target.is_relative_to(root):
                    raise ValueError(f"Archive outside project: {href}")
                key = target.relative_to(root).as_posix()
            ref = {
                "page": relative,
                "source_page": sources.get(relative, OFFICIAL),
                "href": href,
            }
            if ref not in found.setdefault(key, []):
                found[key].append(ref)
    return found


def download_archive(url: str, path: Path) -> dict[str, Any]:
    """Download bytes unchanged; a successful HTTP response must also decompress."""
    try:
        request = Request(url, headers={"User-Agent": "Nebulo-Archive-Audit/1.0"})
        with urlopen(request, timeout=20) as response:
            final_url = response.url
            if urlsplit(final_url).scheme != "https":
                return {
                    "status": "unverified",
                    "detail": "Redirect to an insecure URL",
                    "url": url,
                }
            size = 0
            started = time.monotonic()
            with path.open("wb") as output:
                while chunk := response.read(65536):
                    size += len(chunk)
                    if size > 32_000_000 or time.monotonic() - started > 45:
                        return {
                            "status": "unverified",
                            "detail": "Download limit exceeded",
                            "url": url,
                        }
                    output.write(chunk)
            result = integrity(path)
            return {
                **result,
                "url": url,
                "final_url": final_url,
                "http_status": response.status,
                "bytes": size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
    except HTTPError as error:
        error.close()
        return {
            "status": "broken" if error.code in (404, 410) else "unverified",
            "http_status": error.code,
            "url": url,
            "detail": str(error),
        }
    except (URLError, OSError, ValueError, HTTPException) as error:
        return {"status": "unverified", "url": url, "detail": str(error)}


def remote_integrity(url: str) -> dict[str, Any]:
    """Verify a download using an automatically removed temporary directory."""
    with tempfile.TemporaryDirectory(prefix="nebulo-archive-") as folder:
        path = Path(folder) / ("archive" + Path(urlsplit(url).path).suffix)
        return download_archive(url, path)


def audit(root: Path, check_remote: bool = False) -> dict[str, Any]:
    root = root.resolve()
    refs = references(root)
    paths = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.suffix.lower() in SUFFIXES
    }
    records: list[dict[str, Any]] = []
    for key in sorted(paths | refs.keys()):
        remote = urlsplit(key).scheme in ("http", "https")
        path = None if remote else root / key
        if path is not None and not path.resolve().is_relative_to(root):
            raise ValueError(f"Archive outside project: {path}")
        local = (
            integrity(path)
            if path is not None and path.is_file()
            else {"status": "absent", "detail": "Not stored locally"}
        )
        records.append(
            {
                "path": None if remote else key,
                "source_url": key if remote else source_url(key),
                "references": refs.get(key, []),
                "local": {
                    **local,
                    **(
                        {
                            "bytes": path.stat().st_size,
                            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        }
                        if path is not None and path.is_file()
                        else {}
                    ),
                },
            }
        )
    if check_remote:
        urls = sorted(
            {record["source_url"] for record in records if record["source_url"]}
        )
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = dict(zip(urls, pool.map(remote_integrity, urls), strict=True))
        for record in records:
            if record["source_url"]:
                record["remote"] = results[record["source_url"]]
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "archives": records}


def replace_broken(root: Path, report: dict[str, Any]) -> int:
    """Preflight every target; write all pages before removing the broken files."""
    root = root.resolve()
    broken = [r for r in report["archives"] if r["local"]["status"] == "broken"]
    for record in broken:
        if record.get("remote", {}).get("status") != "valid":
            raise ValueError(
                f"Official archive not verified; no changes made: {record['path']}"
            )
        path = (root / record["path"]).resolve()
        if (
            not path.is_relative_to(root)
            or hashlib.sha256(path.read_bytes()).hexdigest()
            != record["local"]["sha256"]
        ):
            raise ValueError(f"Archive changed since audit: {path}")
    edits: dict[Path, str] = {}
    for record in broken:
        for ref in record["references"]:
            page = (root / ref["page"]).resolve()
            if not page.is_relative_to(root):
                raise ValueError("Page outside project")
            source = edits.get(page, page.read_text(encoding="utf-8"))
            matches = 0

            def update(
                match: re.Match[str],
                expected_href: str = ref["href"],
                target_url: str = record["source_url"],
            ) -> str:
                nonlocal matches
                anchor = match.group()
                attr = HREF.search(anchor)
                if attr is None or html.unescape(attr[2]) != expected_href:
                    return anchor
                matches += 1
                anchor = (
                    anchor[: attr.start(2)]
                    + html.escape(target_url, quote=True)
                    + anchor[attr.end(2) :]
                )
                return (
                    anchor + '<span lang="ro"> (arhivă pe site-ul original; '
                    "necesită internet)</span>"
                )

            updated = ANCHOR.sub(update, source)
            if not matches:
                raise ValueError(f"Link changed since audit: {page}: {ref['href']}")
            edits[page] = updated
    for page, content in edits.items():
        page.write_text(content, encoding="utf-8")
    for record in broken:
        (root / record["path"]).unlink()
        record["action"] = "removed_broken_local_copy; linked_verified_official_archive"
    return len(broken)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--check-remote", action="store_true")
    parser.add_argument("--replace-broken", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.replace_broken and (not args.check_remote or not args.report):
        parser.error("--replace-broken requires --check-remote and --report")
    report = audit(args.root, args.check_remote)
    if args.report:
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if args.replace_broken:
        print(f"Removed {replace_broken(args.root, report)} broken local archives.")
    if args.report:
        args.report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print("Local:", dict(Counter(r["local"]["status"] for r in report["archives"])))
    if args.check_remote:
        print(
            "Remote:",
            dict(
                Counter(
                    r.get("remote", {}).get("status", "unverified")
                    for r in report["archives"]
                )
            ),
        )
    states = {r["local"]["status"] for r in report["archives"] if not r.get("action")}
    states.update(r["remote"]["status"] for r in report["archives"] if "remote" in r)
    return 1 if "broken" in states else 2 if "unverified" in states else 0


if __name__ == "__main__":
    raise SystemExit(main())
