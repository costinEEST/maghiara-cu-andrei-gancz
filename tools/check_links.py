#!/usr/bin/env python3
"""Crawl a local static site, checking files, fragments and optional external URLs.

python3 tools/check_links.py [index.html] [--external] [--json report.json]
No third-party packages required. Exit 1 means confirmed broken links;
exit 2 means external checks were inconclusive (for example rate limiting).
"""

import argparse
import json
import re
import sys
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from urllib.request import Request, urlopen


def srcset_urls(source):
    """Keep commas inside data URLs rather than treating them as local files."""
    position = 0
    while position < len(source):
        while position < len(source) and source[position] in " \t\n\r\f,":
            position += 1
        start = position
        while position < len(source) and not source[position].isspace():
            position += 1
        value = source[start:position]
        if not value:
            break
        yield value.rstrip(",")
        if value.endswith(","):
            continue
        while position < len(source) and source[position] != ",":
            position += 1


class Document(HTMLParser):
    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.refs: list[tuple[str, int]] = []
        self.feed(source)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        # Canonical URLs describe the future public deployment, not navigation.
        if tag == "link" and attributes.get("rel", "") in (
            "canonical",
            "alternate",
            "preconnect",
            "dns-prefetch",
        ):
            return
        identifier = attributes.get("id")
        if identifier:
            self.ids.add(identifier)
        anchor_name = attributes.get("name")
        if tag == "a" and anchor_name:
            self.ids.add(anchor_name)
        for attr in ("href", "src", "poster"):
            value = attributes.get(attr)
            if value:
                self.refs.append((value.strip(), self.getpos()[0]))
        srcset = attributes.get("srcset")
        if srcset:
            for candidate in srcset_urls(srcset):
                self.refs.append((candidate, self.getpos()[0]))


def external_status(url, timeout):
    original = url
    try:
        parsed = urlsplit(url)
        _ = parsed.port  # Validate malformed ports before making a request.
    except ValueError as error:
        return original, None, "broken", f"Malformed URL: {error}"
    url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            quote(parsed.path, safe="/%:@"),
            quote(parsed.query, safe="=&%/:?@,+;"),
            "",
        )
    )
    headers = {"User-Agent": "Nebulo-Link-Checker/1.0 (+static-site-maintenance)"}
    for method in ("HEAD", "GET"):
        try:
            with urlopen(
                Request(url, headers=headers, method=method), timeout=timeout
            ) as response:
                return original, response.status, "ok", response.url
        except HTTPError as error:
            error.close()
            if method == "HEAD":
                continue
            state = "broken" if error.code in (404, 410) else "unverified"
            return original, error.code, state, str(error)
        except (URLError, OSError, ValueError, HTTPException) as error:
            if method == "HEAD":
                continue
            return original, None, "unverified", str(error)


def crawl(entry, check_external=False, timeout=15):
    entry = Path(entry).resolve()
    root = entry.parent
    queue, visited, documents = deque([entry]), set(), {}
    broken, external, ignored = [], {}, set()
    assets = set()

    def parse(path):
        if path not in documents:
            documents[path] = Document(path.read_text(encoding="utf-8"))
        return documents[path]

    while queue:
        path = queue.popleft()
        if path in visited:
            continue
        visited.add(path)
        if not path.is_file():
            broken.append(
                {"page": str(path), "url": str(path), "reason": "Missing entry file"}
            )
            continue
        if path.suffix.lower() == ".css":
            source = path.read_text(encoding="utf-8")
            refs = [
                (m[1], source[: m.start()].count("\n") + 1)
                for m in re.finditer(r'url\(\s*[\'"]?([^\s)\'"]+)', source)
            ]
            refs += [
                (m[1], source[: m.start()].count("\n") + 1)
                for m in re.finditer(r'@import\s+[\'"]([^\'"]+)', source)
            ]
        else:
            refs = parse(path).refs
        for url, line in refs:
            location = {
                "page": path.relative_to(root).as_posix(),
                "line": line,
                "url": url,
            }
            try:
                parsed = urlsplit(url)
                _ = parsed.port
            except ValueError as error:
                broken.append({**location, "reason": f"Malformed URL: {error}"})
                continue
            if parsed.scheme in ("http", "https") or parsed.netloc:
                if not parsed.hostname:
                    broken.append({**location, "reason": "Missing external host"})
                    continue
                if any(char in url for char in '<>"'):
                    broken.append(
                        {
                            **location,
                            "reason": "Malformed external URL contains HTML markup",
                        }
                    )
                    continue
                normalized = urlunsplit(
                    (
                        parsed.scheme or "https",
                        parsed.netloc,
                        parsed.path,
                        parsed.query,
                        "",
                    )
                )
                external.setdefault(normalized, []).append(location)
                continue
            if parsed.scheme:
                if parsed.scheme not in ("mailto", "tel", "data", "blob"):
                    broken.append({**location, "reason": "Unsupported URL scheme"})
                else:
                    ignored.add(parsed.scheme)
                continue
            target = (
                (
                    root / unquote(parsed.path).lstrip("/")
                    if parsed.path.startswith("/")
                    else path.parent / unquote(parsed.path)
                )
                if parsed.path
                else path
            )
            if target.is_dir():
                target = target / "index.html"
            target = target.resolve()
            if not target.is_relative_to(root):
                broken.append(
                    {**location, "reason": "Link escapes the standalone site"}
                )
                continue
            if not target.is_file():
                broken.append({**location, "reason": "Missing local file"})
                continue
            assets.add(target)
            if target.suffix.lower() in (".html", ".htm", ".css"):
                queue.append(target)
            if parsed.fragment and target.suffix.lower() in (".html", ".htm"):
                fragment = unquote(parsed.fragment).split(":~:text=")[0]
                if fragment and fragment not in parse(target).ids:
                    broken.append(
                        {**location, "reason": "Missing fragment #" + fragment}
                    )
    external_results = []
    if check_external:
        with ThreadPoolExecutor(max_workers=6) as executor:
            for url, status, state, detail in executor.map(
                lambda url: external_status(url, timeout), external
            ):
                result = {
                    "url": url,
                    "status": status,
                    "state": state,
                    "detail": detail,
                    "referrers": external[url],
                }
                external_results.append(result)
                if state == "broken":
                    broken.append(
                        {
                            "url": url,
                            "reason": f"HTTP {status}"
                            if status is not None
                            else detail,
                            "referrers": external[url],
                        }
                    )
    return {
        "entry": str(entry),
        "html_pages": len(documents),
        "local_files": len(assets),
        "external_urls": len(external),
        "external_checked": check_external,
        "broken": broken,
        "unverified_external": [
            r for r in external_results if r["state"] == "unverified"
        ],
        "external_results": external_results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "entry",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "index.html",
    )
    parser.add_argument(
        "--external",
        action="store_true",
        help="Also check HTTP(S) links; requires internet",
    )
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--json", type=Path, help="Save the full report")
    args = parser.parse_args()
    report = crawl(args.entry, args.external, args.timeout)
    print(
        f"Checked {report['html_pages']} HTML pages and "
        f"{report['local_files']} local files; "
        f"{report['external_urls']} distinct external URLs."
    )
    for error in report["broken"]:
        print(
            f"BROKEN {error.get('page', '')}:{error.get('line', '')} "
            f"{error['url']} — {error['reason']}"
        )
    print(
        f"Broken: {len(report['broken'])}; "
        f"unverified external: {len(report['unverified_external'])}."
    )
    if not args.external:
        print("External URLs skipped. Use --external to check them.")
    if args.json:
        args.json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return 1 if report["broken"] else 2 if report["unverified_external"] else 0


if __name__ == "__main__":
    sys.exit(main())
