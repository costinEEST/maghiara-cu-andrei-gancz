"""Mark external navigation links; default is a read-only audit, --write applies.

Keep same-site links, downloads, fragments and non-web schemes unchanged.
Only edit anchor markup; never reserialize lesson text or execute JavaScript.
"""

import argparse
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from html_attributes import ATTRIBUTES

ROOT = Path(__file__).resolve().parents[1]
MARKER = (
    '<span aria-hidden="true" class="external-icon">↗</span>'
    '<span class="visually-hidden" lang="ro"> (site extern)</span>'
)


def is_external(href, public_url):
    parsed = urlsplit(href)
    if not parsed.scheme and not parsed.netloc:
        return False
    target, site = urlsplit(urljoin(public_url, href)), urlsplit(public_url)
    if target.scheme not in {"http", "https"}:
        return False

    def origin(url):
        return (
            url.scheme,
            url.hostname,
            url.port or (443 if url.scheme == "https" else 80),
        )

    return origin(target) != origin(site) or not (
        target.path == site.path.rstrip("/") or target.path.startswith(site.path)
    )


class ExternalLinks(HTMLParser):
    def __init__(self, source, public_url):
        super().__init__(convert_charrefs=False)
        self.source, self.public_url = source, public_url
        self.offsets = [0] + [m.end() for m in re.finditer("\n", source)]
        self.active = None
        self.edits = []

    def source_offset(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        attributes = dict(attrs)
        href = attributes.get("href")
        if href and is_external(href, self.public_url):
            if self.active is not None:
                raise ValueError("Nested external anchors")
            self.active = (
                self.source_offset(),
                attributes,
                len(self.get_starttag_text() or ""),
            )

    def handle_endtag(self, tag):
        if tag != "a" or self.active is None:
            return
        start, attrs, opening_end = self.active
        closing = self.source_offset()
        end = self.source.index(">", closing) + 1
        original = self.source[start:end]
        opening = original[:opening_end]
        body = original[opening_end : closing - start]
        rel = str(attrs.get("rel") or "").split()
        if "noreferrer" not in [token.lower() for token in rel]:
            rel.append("noreferrer")
            value = ' rel="' + html.escape(" ".join(rel), quote=True) + '"'
            match = next(
                (
                    m
                    for m in ATTRIBUTES.finditer(opening)
                    if m[1].split("=")[0].strip().lower() == "rel"
                ),
                None,
            )
            opening = (
                opening[: match.start()] + value + opening[match.end() :]
                if match
                else opening[:-1] + value + ">"
            )
        doc = BeautifulSoup("<div>" + body + "</div>", "html.parser")
        if not doc.select_one(".external-icon"):
            body += MARKER
        updated = opening + body + self.source[closing:end]
        if updated != original:
            self.edits.append((start, end, updated))
        self.active = None


def mark_html(source, public_url):
    parser = ExternalLinks(source, public_url)
    parser.feed(source)
    parser.close()
    if parser.active is not None:
        raise ValueError("Unclosed external anchor")
    for start, end, value in reversed(parser.edits):
        source = source[:start] + value + source[end:]
    return source


def mark_site(root=ROOT, *, write=False):
    root = Path(root).resolve()
    base = json.loads((root / "site-config.json").read_text(encoding="utf-8"))[
        "public_url"
    ]
    base = base.rstrip("/") + "/"
    changes = {}
    for path in sorted(root.rglob("*.html")):
        if any(
            part in {".git", "node_modules", ".venv"}
            for part in path.relative_to(root).parts
        ):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("HTML path escapes site")
        source = path.read_text(encoding="utf-8")
        marked = mark_html(source, base)
        if marked != source:
            changes[path] = marked
    if write:
        for path, value in changes.items():
            path.write_text(value, encoding="utf-8")
    return [p.relative_to(root).as_posix() for p in changes]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        changes = mark_site(args.root, write=args.write)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"External link audit failed: {error}\n")
    print(f"{'Updated' if args.write else 'Pending'} HTML files: {len(changes)}")
    return int(bool(changes) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
