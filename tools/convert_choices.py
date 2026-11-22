"""Convert standalone short single-answer questions to accessible radio groups.

Keep cloze, matching/ordering selects and long option lists unchanged. Default
is a read-only audit; --write preflights all pages before applying changes.
"""

import argparse
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]


def convert_page(source):
    doc = BeautifulSoup(source, "html.parser")
    content = doc.select_one(".lesson-content")
    if content is None:
        return source, 0
    if any("Asociază fiecare element" in n.get_text() for n in content.select(".note")):
        return source, 0
    edits = []
    identifiers = {str(n.get("id")) for n in doc.select("[id]")}
    for field in content.select("select[data-answers]:not([data-cloze])"):
        if field.has_attr("multiple"):
            continue
        options = [o for o in field.select("option") if o.get("value") != ""]
        if not 2 <= len(options) <= 5:
            continue
        label = field.find_parent("label")
        if label is None:
            continue
        paragraph = label.parent
        if paragraph is None or paragraph.name != "p":
            continue
        if len(paragraph.find_all(["input", "select"])) != 1:
            continue
        if paragraph.get_text(" ", strip=True) != label.get_text(" ", strip=True):
            continue
        if not doc.select_one("[data-check]"):
            raise ValueError("Radio conversion requires shared exercise controls")
        raw = field.get("data-answers")
        if not isinstance(raw, str):
            raise ValueError("Answer key must be JSON text")
        answers = json.loads(raw)
        values = [
            str(o["value"]) if o.has_attr("value") else " ".join(o.get_text().split())
            for o in options
        ]
        if (
            not isinstance(answers, list)
            or not answers
            or any(" ".join(answer.split()) not in values for answer in answers)
        ):
            raise ValueError("Accepted answers must be available choices")
        if len(set(values)) != len(values):
            raise ValueError("Duplicate answer choices")
        identifier = str(field.get("id", ""))
        if not identifier:
            raise ValueError("Missing question id")
        group = doc.new_tag(
            "fieldset",
            attrs={
                "class": "choice-question",
                "data-choice": "",
                "data-answers": raw,
                "id": identifier,
            },
        )
        for attr in ("aria-describedby", "aria-label"):
            if field.has_attr(attr):
                group[attr] = field[attr]
        legend = doc.new_tag("legend")
        # Preserve the original question and embedded Hungarian language spans.
        for child in list(label.contents):
            if child is field:
                continue
            if getattr(child, "name", None) == "br":
                continue
            legend.append(child.extract())
        text = legend.get_text(" ", strip=True)
        if re.fullmatch(r"\d+\.?", text):
            legend.clear()
            legend["lang"] = "ro"
            legend.string = f"Întrebarea {len(edits) + 1}"
        else:
            legend["lang"] = str(label.get("lang", "hu"))
        group.append(legend)
        for number, (option, value) in enumerate(zip(options, values, strict=True), 1):
            control_id = f"{identifier}-optiunea-{number}"
            if control_id in identifiers:
                raise ValueError(f"Duplicate generated id: {control_id}")
            identifiers.add(control_id)
            choice = doc.new_tag(
                "label", attrs={"class": "choice-option", "for": control_id}
            )
            radio = doc.new_tag(
                "input",
                attrs={
                    "type": "radio",
                    "name": identifier + "-alegere",
                    "id": control_id,
                    "value": value,
                },
            )
            choice.append(radio)
            passage = doc.new_tag("span")
            bilingual = re.fullmatch(r"(Igaz|Hamis)\s*—\s*(adevărat|fals)", value)
            if bilingual:
                hu = doc.new_tag("span", lang="hu")
                hu.string = bilingual[1]
                ro = doc.new_tag("span", lang="ro")
                ro.string = " — " + bilingual[2]
                passage.append(hu)
                passage.append(ro)
            else:
                passage["lang"] = str(option.get("lang", field.get("lang", "hu")))
                passage.string = option.get_text()
            choice.append(passage)
            group.append(choice)
        # Replace only the standalone paragraph, preserving all other lesson HTML.
        pattern = re.compile(
            r'<p\b[^>]*>\s*<label\b[^>]*\bfor="'
            + re.escape(identifier)
            + r'"[^>]*>.*?</label\s*>\s*</p>',
            re.S,
        )
        if len(pattern.findall(source)) != 1:
            raise ValueError(f"Ambiguous standalone question: {identifier}")
        edits.append((pattern, serialize_html(group)))
    for pattern, replacement in edits:
        source = pattern.sub(
            lambda _, replacement=replacement: replacement, source, count=1
        )
    if edits:
        note = (
            '<p class="note single-choice-instructions" lang="ro">'
            "Alege o singură variantă pentru fiecare întrebare.</p>"
        )
        source = source.replace(edits[0][1], note + edits[0][1], 1)
    return source, len(edits)


def convert_site(root=ROOT, *, write=False):
    root = Path(root).resolve()
    edits = {}
    count = 0
    for path in sorted(root.rglob("*.html")):
        if any(
            part in {".git", "node_modules", ".venv"}
            for part in path.relative_to(root).parts
        ):
            continue
        if not path.resolve().is_relative_to(root):
            raise ValueError("HTML path escapes site")
        source = path.read_text(encoding="utf-8")
        try:
            converted, number = convert_page(source)
        except ValueError as error:
            raise ValueError(f"{path}: {error}") from error
        if number:
            edits[path] = converted
            count += number
    if write:
        for path, source in edits.items():
            path.write_text(source, encoding="utf-8")
    return {
        "questions": count,
        "pages": [p.relative_to(root).as_posix() for p in edits],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = convert_site(args.root, write=args.write)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot convert choices: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result["questions"]) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
