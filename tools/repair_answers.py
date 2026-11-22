"""Recover cloze keys from supplied original HTML; never execute source scripts.

Source files use the local exercise filenames. This preflights every page before
writing, and is read-only unless --write is supplied. Sources stay outside the site.
"""

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ASSIGNMENT = re.compile(
    r"I\[(\d+)\]\[1\]\[\d+\]\[0\]\s*=\s*"
    r"('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")\s*;",
    re.S,
)
CONTROL = re.compile(r"<(?:input|select)\b[^>]*>", re.I)
DISCLOSURE = re.compile(r'<details\b[^>]*class="solutions"[^>]*>.*?</details>', re.S)


def source_text(raw: bytes) -> str:
    charset = re.search(rb"charset\s*=\s*[\"']?([^\s\"'/>;]+)", raw, re.I)
    encoding = charset[1].decode("ascii") if charset else "utf-8"
    return raw.decode(encoding)


def decode_literal(literal: str) -> str:
    """Decode JS escapes as string data, not executable expressions."""
    escapes = {
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "b": "\b",
        "f": "\f",
        "v": "\v",
        "0": "\0",
    }

    def replace(match: re.Match[str]) -> str:
        value = match[1]
        if value.startswith(("u", "x")):
            return chr(int(value[1:], 16))
        return escapes.get(value, value if value not in ("\n", "\r\n") else "")

    inner = re.sub(
        r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|\r\n|.)",
        replace,
        literal[1:-1],
        flags=re.S,
    )
    decoded = inner.encode("utf-16-le", errors="surrogatepass").decode("utf-16-le")
    return unicodedata.normalize("NFC", html.unescape(decoded)).strip()


def answer_keys(source: str) -> dict[str, list[str]]:
    keys: dict[str, list[str]] = {}
    for match in ASSIGNMENT.finditer(source):
        answer = decode_literal(match[2])
        if not answer:
            raise ValueError("Empty source answer")
        values = keys.setdefault("Gap" + match[1], [])
        if answer not in values:
            values.append(answer)
    if not keys:
        raise ValueError("No supported source answer keys found")
    return keys


def repair_page(source: str, original: str) -> tuple[str, int]:
    doc = BeautifulSoup(source, "html.parser")
    controls = [
        node
        for node in doc.select("input[id],select[id]")
        if re.fullmatch(r"Gap\d+", str(node.get("id", "")))
    ]
    keys = answer_keys(original)
    identifiers = [str(node["id"]) for node in controls]
    if len(set(identifiers)) != len(identifiers) or set(identifiers) != set(keys):
        raise ValueError("Source keys do not match local gaps")
    extras: dict[str, list[str]] = {}
    for node in controls:
        if node.name == "select":
            options = {
                str(option.get("value", option.get_text()))
                for option in node.select("option")
            }
            name = str(node["id"])
            for index, answer in enumerate(keys[name]):
                if answer not in options:
                    candidate = re.sub(
                        r"u([0-9a-fA-F]{4})",
                        lambda match: chr(int(match[1], 16)),
                        answer,
                    )
                    matching = [
                        option
                        for option in options
                        if option.casefold() == candidate.casefold()
                    ]
                    if len(matching) == 1:
                        keys[name][index] = matching[0]
                    elif candidate != answer:
                        raise ValueError("Unconfirmed malformed source escape")
                    else:
                        extras.setdefault(name, []).append(answer)
    if len(doc.select("details.solutions")) != 1:
        raise ValueError("Expected exactly one solutions disclosure")
    items = "".join(
        '<li lang="hu">' + html.escape(" / ".join(keys[name])) + "</li>"
        for name in identifiers
    )
    disclosure = (
        '<details class="solutions"><summary>Vezi răspunsurile</summary><ol>'
        + items
        + "</ol></details>"
    )
    actions = (
        ""
        if doc.select_one("[data-check]")
        else (
            '<div class="exercise-actions"><button data-check="" type="button">'
            'Verifică răspunsurile</button><button data-reset="" type="button">'
            "Reia exercițiul</button></div>"
            '<p class="feedback" role="status" aria-live="polite"></p>'
        )
    )

    def update(match: re.Match[str]) -> str:
        opening = match.group()
        identifier = re.search(r'\bid="(Gap\d+)"', opening)
        if identifier is None:
            return opening
        name = identifier[1]
        opening = re.sub(
            r'\s+(?:lang|data-answers)=(?:\'[^\']*\'|"[^"]*")', "", opening
        )
        data = html.escape(json.dumps(keys[name], ensure_ascii=False), quote=True)
        cloze = ' data-cloze=""' if opening.lower().startswith("<select") else ""
        return opening[:-1] + f' lang="hu" data-answers="{data}"{cloze}>'

    result = CONTROL.sub(update, source)

    def add_options(match: re.Match[str]) -> str:
        identifier = re.search(r'\bid="(Gap\d+)"', match[1])
        values = extras.get(identifier[1], []) if identifier else []
        options = "".join(
            '<option lang="hu" value="'
            + html.escape(value, quote=True)
            + '">'
            + html.escape(value)
            + "</option>"
            for value in values
        )
        return match[1] + match[2] + options + match[3]

    result = re.sub(
        r"(<select\b[^>]*>)(.*?)(</select>)", add_options, result, flags=re.S
    )
    result = re.sub(r'(<option\b[^>]*\blang=)"ro"', r'\1"hu"', result)
    result, count = DISCLOSURE.subn(lambda _: actions + disclosure, result)
    if count != 1:
        raise ValueError("Cannot safely replace solutions")
    result = result.replace(
        "Completează activitatea înainte de a\n            consulta răspunsurile.",
        "Poți completa activitatea sau consulta oricând răspunsurile.",
    )
    return result, len(controls)


def repair(root: Path, sources: Path, write: bool = False) -> tuple[int, int]:
    root = root.resolve()
    records = json.loads((root / "assets/inventory.json").read_text(encoding="utf-8"))[
        "pages"
    ]
    edits: list[tuple[Path, str, int]] = []
    for record in records:
        path = (root / record["path"]).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Page outside project")
        source = path.read_text(encoding="utf-8")
        doc = BeautifulSoup(source, "html.parser")
        empty = any(
            not detail.select("li") for detail in doc.select("details.solutions")
        )
        missing = any(
            re.fullmatch(r"Gap\d+", str(node.get("id", "")))
            and not node.has_attr("data-answers")
            for node in doc.select("input,select")
        )
        if empty or missing:
            original = source_text((sources / path.name).read_bytes())
            updated, count = repair_page(source, original)
            edits.append((path, updated, count))
    if write:
        for path, source, _ in edits:
            path.write_text(source, encoding="utf-8")
    return len(edits), sum(count for _, _, count in edits)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    pages, fields = repair(args.root, args.sources, args.write)
    print(
        f"{'Repaired' if args.write else 'Preflighted'} "
        f"{pages} pages and {fields} answer fields."
    )


if __name__ == "__main__":
    main()
