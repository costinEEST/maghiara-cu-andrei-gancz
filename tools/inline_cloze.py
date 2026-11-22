"""Flatten unambiguous cloze layout tables and style inline typing fields.

Preserve translation, comparison, paradigm and image tables. Default is a
read-only audit; --write applies only after all changed pages preflight.
"""

import argparse
import copy
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]
GAP = re.compile(r"Gap\d+$")


def compact(text):
    return re.sub(r"\s+", " ", text).strip()


def auxiliary(text):
    return not text or bool(
        re.fullmatch(r"\d+\.?|[\w .-]{1,40}:|[\u2013—-]|\([^()]+\)", text)
    )


def layout_rows(table):
    """Accept numbered exercises or speaker/line layouts, not parallel readings."""
    if table.find(["table", "th", "img"]) or table.find("caption"):
        return None
    rows = [r for r in table.find_all("tr") if r.find_parent("table") is table]
    if not rows:
        return None
    for row in rows:
        cells = row.find_all(["td", "th"], recursive=False)
        significant = [
            c for c in cells if compact(c.get_text()) or c.find(["input", "select"])
        ]
        if not significant:
            continue
        # Every text-only side cell must be an exercise number, speaker or cue.
        # Free-standing text is allowed only as the sole substantive cell.
        substantive = [
            c
            for c in significant
            if not auxiliary(compact(c.get_text())) or c.find(["input", "select"])
        ]
        if len(substantive) > 1:
            # Multiple independent exercises need explicit numbered delimiters.
            numbers = [
                c for c in significant if re.fullmatch(r"\d+\.?", compact(c.get_text()))
            ]
            if len(numbers) < len(substantive):
                return None
        for cell in significant:
            if cell.has_attr("rowspan") and str(cell["rowspan"]) != "1":
                return None
    return rows


def flatten_table(table, doc):
    rows = layout_rows(table)
    if rows is None:
        return None
    flow = doc.new_tag("div", attrs={"class": "cloze-flow"})
    if table.get("id"):
        flow["id"] = table["id"]
    for row in rows:
        item = None
        pending = []
        for cell in row.find_all(["td", "th"], recursive=False):
            text = compact(cell.get_text())
            if not text and not cell.find(["input", "select"]):
                continue
            if re.fullmatch(r"\d+\.?", text):
                item = doc.new_tag("div", attrs={"class": "cloze-item"})
                label = doc.new_tag("p", attrs={"class": "cloze-number", "lang": "ro"})
                label.string = text
                item.append(label)
                flow.append(item)
                pending = []
                continue
            if item is None:
                item = doc.new_tag("div", attrs={"class": "cloze-item"})
                flow.append(item)
            paragraph = doc.new_tag("div", attrs={"class": "cloze-line"})
            # Keep explicit languages. Native dialogue text is Hungarian; cues
            # and nested Romanian passages retain their own existing labels.
            inherited = cell
            language = None
            while isinstance(inherited, Tag):
                if inherited.get("lang"):
                    language = str(inherited["lang"])
                    break
                if inherited is table:
                    break
                inherited = inherited.parent
            if language is None:
                first = row.find(["td", "th"], recursive=False)
                speaker = (
                    first is not None
                    and compact(first.get_text()).endswith(":")
                    and compact(first.get_text()) != "Exemplu:"
                )
                language = (
                    "hu"
                    if table.select('input[lang="hu"],select[lang="hu"]') or speaker
                    else "ro"
                )
            paragraph["lang"] = language
            if auxiliary(text) and not cell.find(["input", "select"]):
                pending.append(copy.deepcopy(cell))
                continue
            for cue in pending:
                span = doc.new_tag("span")
                span["lang"] = str(
                    cue.get(
                        "lang", "ro" if compact(cue.get_text()) == "Exemplu:" else "hu"
                    )
                )
                for child in list(cue.contents):
                    span.append(child.extract())
                paragraph.append(span)
                paragraph.append(" ")
            pending = []
            for child in cell.contents:
                paragraph.append(copy.deepcopy(child))
            item.append(paragraph)
        if pending:
            for cue in pending:
                paragraph = doc.new_tag("div", attrs={"class": "cloze-line"})
                for child in list(cue.contents):
                    paragraph.append(child.extract())
                if item is None:
                    flow.append(paragraph)
                else:
                    item.append(paragraph)
    return flow


def transform_page(source):
    doc = BeautifulSoup(source, "html.parser")
    content = doc.select_one(".lesson-content")
    if content is None:
        return source, 0, 0
    changes = []
    inputs = 0
    for field in content.select('input[data-answers][type="text"]'):
        if not GAP.fullmatch(str(field.get("id", ""))):
            continue
        if "cloze-input" in field.get_attribute_list("class"):
            continue
        identifier = str(field["id"])
        field["class"] = " ".join([*field.get_attribute_list("class"), "cloze-input"])
        field["size"] = "12"
        field["autocomplete"] = "off"
        field["autocapitalize"] = "none"
        field["spellcheck"] = "false"
        pattern = re.compile(
            r'<input\b[^>]*\bid="' + re.escape(identifier) + r'"[^>]*>', re.S
        )
        if len(pattern.findall(source)) != 1:
            raise ValueError(f"Ambiguous input id: {identifier}")
        changes.append((pattern, serialize_html(field)))
        inputs += 1
    for pattern, replacement in changes:
        source = pattern.sub(
            lambda _, replacement=replacement: replacement, source, count=1
        )
    # Reparse so copied table contents include the updated input markup.
    doc = BeautifulSoup(source, "html.parser")
    content = doc.select_one(".lesson-content")
    assert content is not None
    tables = 0
    for table in list(content.select("table")):
        if table.find_parent("table") is not None:
            continue
        if not table.select("input.cloze-input,select[data-cloze]"):
            first_cells = [
                row.find(["td", "th"], recursive=False) for row in table.find_all("tr")
            ]
            if not any(
                cell
                and re.fullmatch(r"\d+\.?|[\w .-]{1,40}:", compact(cell.get_text()))
                for cell in first_cells
            ):
                continue
        flow = flatten_table(table, doc)
        if flow is None:
            continue
        wrapper = table.parent
        if isinstance(wrapper, Tag) and "table-scroll" in wrapper.get_attribute_list(
            "class"
        ):
            if len(wrapper.find_all(recursive=False)) != 1:
                raise ValueError("Unexpected content beside layout table")
            target = wrapper
            if wrapper.get("id"):
                flow["id"] = wrapper["id"]
        else:
            target = table
        # Match the unique table region by its prevalidated aria label or id.
        markup = serialize_html(target)
        original_doc = BeautifulSoup(source, "html.parser")
        if target is wrapper and target.get("aria-label"):
            region = str(target["aria-label"])
            node = original_doc.find("div", attrs={"aria-label": region})
        else:
            node = next(
                (
                    n
                    for n in original_doc.select("table")
                    if serialize_html(n) == markup
                ),
                None,
            )
        if node is None:
            raise ValueError("Cannot locate layout table")
        # Find raw bounds using its unique anchor attribute; tables accepted
        # above have no nested tables, so the first closing table ends the region.
        if target is wrapper:
            label = re.escape(str(target.get("aria-label", "")))
            pattern = re.compile(
                r'<div\b[^>]*aria-label="'
                + label
                + r'"[^>]*>\s*<table\b.*?</table>\s*</div>',
                re.S,
            )
        else:
            pattern = re.compile(r"<table\b[^>]*>.*?</table>", re.S)
            candidates = []
            for match in pattern.finditer(source):
                parsed_table = BeautifulSoup(match[0], "html.parser").table
                if parsed_table is not None and serialize_html(parsed_table) == markup:
                    candidates.append(match)
            if len(candidates) != 1:
                raise ValueError("Ambiguous bare layout table")
            match = candidates[0]
            source = (
                source[: match.start()] + serialize_html(flow) + source[match.end() :]
            )
            tables += 1
            continue
        if len(pattern.findall(source)) != 1:
            raise ValueError("Ambiguous layout region")
        source = pattern.sub(lambda _, flow=flow: serialize_html(flow), source, count=1)
        tables += 1
    if inputs:
        source = re.sub(
            r"Pentru a înscrie literele[^<]{0,260}?butoanele de sub exercițiu\.",
            "",
            source,
        )
        source = re.sub(
            r"Pute[țţ]i folosi butonul „Ajutor”,[^<]{0,160}?rezultatul\.", "", source
        )
        source = re.sub(r"în dreptunghiurile\s+albe", "în câmpurile subliniate", source)
    return source, inputs, tables


def transform_site(root=ROOT, *, write=False):
    root = Path(root).resolve()
    updates = {}
    inputs = tables = 0
    for path in sorted(root.rglob("*.html")):
        if any(
            p in {".git", "node_modules", ".venv"} for p in path.relative_to(root).parts
        ):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("HTML path escapes site")
        original = path.read_text(encoding="utf-8")
        try:
            updated, count, flat = transform_page(original)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error
        if updated != original:

            def keys(s):
                return {
                    str(n.get("id")): str(n["data-answers"])
                    for n in BeautifulSoup(s, "html.parser").select("[data-answers]")
                }

            if keys(original) != keys(updated):
                raise ValueError(f"Changed answer keys: {path}")
            before, after = (
                BeautifulSoup(s, "html.parser") for s in (original, updated)
            )
            if {str(n["id"]) for n in before.select("[id]")} != {
                str(n["id"]) for n in after.select("[id]")
            }:
                raise ValueError(f"Changed fragment IDs: {path}")

            def visible(document):
                body = document.select_one(".lesson-content")
                assert body is not None
                for note in body.select(".note"):
                    note.decompose()
                return re.sub(r"\s+", "", body.get_text())

            if visible(before) != visible(after):
                raise ValueError(f"Changed lesson text: {path}")
            updates[path] = updated
            inputs += count
            tables += flat
    if write:
        for path, updated in updates.items():
            path.write_text(updated, encoding="utf-8")
    return {
        "inputs": inputs,
        "tables": tables,
        "pages": [p.relative_to(root).as_posix() for p in updates],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = transform_site(args.root, write=args.write)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot normalize cloze layout: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result["pages"]) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
