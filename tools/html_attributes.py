"""Normalize HTML attribute quotes without reformatting lesson text.

Default: read-only audit. Use --write to apply after all files preflight.
HTMLHint remains the source-level check for unquoted or malformed attributes.
"""

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.dammit import EntitySubstitution
from bs4.element import Tag
from bs4.formatter import HTMLFormatter

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTES = re.compile(r"""(\s+[^\s"'<>/=]+\s*=\s*)("[^"]*"|'[^']*'|[^\s>]+)""")


class DoubleQuotedFormatter(HTMLFormatter):
    """Keep JSON quotes as entities rather than changing the outer delimiter."""

    @classmethod
    def quoted_attribute_value(cls, value: str) -> str:
        return '"' + value.replace('"', "&#34;") + '"'


def serialize_html(node: Tag) -> str:
    formatter = DoubleQuotedFormatter(
        entity_substitution=EntitySubstitution.substitute_xml
    )
    return node.decode(formatter=formatter)


class AttributeQuotes(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.offsets = [0] + [match.end() for match in re.finditer("\n", source)]
        self.edits: list[tuple[int, int, str]] = []

    def handle_starttag(self, tag, attrs):
        opening = self.get_starttag_text()
        if opening is None:
            return
        line, column = self.getpos()
        offset = self.offsets[line - 1] + column
        for match in ATTRIBUTES.finditer(opening):
            value = match[2]
            if value.startswith(("'", '"')):
                content = value[1:-1].replace("&quot;", "&#34;")
                replacement = '"' + content.replace('"', "&#34;") + '"'
                if replacement == value:
                    continue
                self.edits.append(
                    (offset + match.start(2), offset + match.end(2), replacement)
                )

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def normalize_quotes(source: str) -> str:
    parser = AttributeQuotes(source)
    parser.feed(source)
    parser.close()
    for start, end, replacement in reversed(parser.edits):
        source = source[:start] + replacement + source[end:]
    return source


def normalize_site(root=ROOT, *, write=False):
    root = Path(root).resolve()
    updates = {}
    for path in sorted(root.rglob("*.html")):
        relative = path.relative_to(root)
        if any(part in {".git", "node_modules", ".venv"} for part in relative.parts):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"HTML path escapes site: {relative}")
        source = path.read_text(encoding="utf-8")
        normalized = normalize_quotes(source)
        if source != normalized:
            # Check decoded JSON attributes, text, language labels and structure,
            # not only the appearance of the resulting source.
            before = BeautifulSoup(source, "html.parser").decode()
            after = BeautifulSoup(normalized, "html.parser").decode()
            if before != after:
                raise ValueError(f"Attribute normalization changed the DOM: {relative}")
            updates[path] = normalized
    if write:
        for path, normalized in updates.items():
            path.write_text(normalized, encoding="utf-8")
    return [path.relative_to(root).as_posix() for path in updates]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true", help="Read-only audit (default)")
    args = parser.parse_args(argv)
    try:
        changed = normalize_site(args.root, write=args.write)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Cannot normalize HTML attributes: {error}\n")
    print(f"{'Updated' if args.write else 'Nonconforming'} HTML files: {len(changed)}")
    return int(bool(changed) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
