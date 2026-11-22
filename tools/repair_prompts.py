"""Audit exercises against supplied originals and restore lost radio-quiz prompts.

Original files are named after local exercise pages in an external --sources
folder. Default is read-only; --write applies only after all pages preflight.
Never executes the original JavaScript or invents a prompt from an answer key.
"""

import argparse
import html
import json
import re
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]


def compact(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def comparable(value):
    return re.sub(r"\s+", "", unicodedata.normalize("NFC", value))


def decode_source(raw):
    match = re.search(rb"""charset\s*=\s*["']?([^\s"'/>;]+)""", raw, re.I)
    if match:
        return raw.decode(match[1].decode("ascii"))
    try:
        return raw.decode("utf-8-sig")
    except UnicodeError:
        return raw.decode("cp1250")


def option_text(radio):
    pieces = []
    for sibling in radio.next_siblings:
        if isinstance(sibling, Tag):
            if sibling.name in {"input", "br", "td", "tr", "table"}:
                break
            pieces.append(sibling.get_text(" ", strip=True))
        elif isinstance(sibling, NavigableString):
            pieces.append(str(sibling))
    text = compact(" ".join(pieces))
    if not text:
        cell = radio.find_parent("td")
        if cell:
            for child in cell.contents:
                if isinstance(child, Tag) and child.name in {"input", "br", "td", "tr"}:
                    break
                pieces.append(
                    child.get_text(" ", strip=True)
                    if isinstance(child, Tag)
                    else str(child)
                )
        text = compact(" ".join(pieces))
        if not text and cell:
            adjacent = cell.find_next_sibling("td")
            while adjacent and not adjacent.find("input"):
                candidate = compact(adjacent.get_text(" ", strip=True))
                if candidate:
                    if re.match(r"^[a-z]\.\s", candidate):
                        text = candidate
                    break
                adjacent = adjacent.find_next_sibling("td")
    return text


def source_questions(source):
    if not re.search(r"""<input\b[^>]*\btype\s*=\s*["']?radio\b""", source, re.I):
        return None, []
    # HTML5 table recovery is essential: some originals omit almost every td/tr
    # closing tag. The standard parser nests later questions inside earlier ones.
    source = re.sub(r"^\s*<\?xml[^>]*\?>", "", source)
    doc = BeautifulSoup(source, "html5lib")
    # Odd-word tasks use the option groups themselves, with one overall task
    # instruction. There is no separate stimulus to restore for each group.
    if "Găsiți intrusul" in doc.get_text(" ", strip=True):
        return doc, []
    groups = {}
    for radio in doc.select('input[type="radio"]'):
        onclick = str(radio.get("onclick", ""))
        match = re.search(r"answer\[(\d+)\]\s*=\s*['\"]([a-zA-Z]+)['\"]", onclick)
        if match is None:
            raise ValueError("Unsupported original radio handler")
        index = int(match[1])
        groups.setdefault(index, []).append((match[2], radio))
    result = []
    for index in sorted(groups):
        radios = groups[index]
        letters = [letter for letter, _ in radios]
        booleans = {
            "igaz": "Igaz — adevărat",
            "hamis": "Hamis — fals",
            "Da": "Da",
            "Nu": "Nu",
        }
        options = [
            option_text(radio) or booleans.get(letter, "") for letter, radio in radios
        ]
        if len(set(letters)) != len(letters) or not all(options):
            raise ValueError("Ambiguous original radio options")
        row = radios[0][1].find_parent("tr")
        if row is None:
            raise ValueError("Original radio has no question row")
        prompt, suffix = "", False
        radio_cell = radios[0][1].find_parent("td")
        cells = row.find_all(["td", "th"], recursive=False)
        for cell in cells:
            text = compact(cell.get_text(" ", strip=True))
            if re.match(r"^[a-z]\.\s", text):
                continue
            if not cell.find("input") and text and not re.fullmatch(r"\d+\.?", text):
                if prompt:
                    raise ValueError("Multiple original prompt cells")
                prompt = text
                suffix = radio_cell in cells and cells.index(cell) > cells.index(
                    radio_cell
                )
        if not prompt:
            previous = row.find_previous_sibling("tr")
            if previous and not previous.find("input"):
                text = compact(previous.get_text(" ", strip=True))
                if re.match(rf"^{index + 1}\.\s+\S", text):
                    prompt = text
        if not prompt:
            following = row.find_next_sibling("tr")
            if following and not following.find("input"):
                text = compact(following.get_text(" ", strip=True))
                if text.startswith(("\u2013", "—")):
                    prompt = text
        prompt = re.sub(r"^\d+\.\s*", "", prompt)
        if suffix:
            prompt = "… " + prompt
        key = re.search(rf"""key\[{index}\]\s*=\s*["']([a-zA-Z]+)["']""", source)
        if key is None or key[1] not in letters:
            raise ValueError("Missing original radio key")
        result.append(
            {
                "index": index,
                "prompt": prompt,
                "options": options,
                "answer_index": letters.index(key[1]),
            }
        )
    return doc, result


def repair_page(source, original):
    original_doc, questions = source_questions(original)
    if not questions:
        return source, 0
    doc = BeautifulSoup(source, "html.parser")
    groups = doc.select("fieldset[data-choice][data-answers]")
    if groups:
        if len(groups) != len(questions):
            raise ValueError("Original questions do not match radio groups")
        for group, question in zip(groups, questions, strict=True):
            legend = group.find("legend")
            if legend is None:
                raise ValueError("Radio question has no legend")
            prompt = re.sub(r"^\d+\.\s*", "", legend.get_text(" ", strip=True))
            if question["prompt"] and comparable(prompt) != comparable(
                question["prompt"]
            ):
                raise ValueError("Radio question lost its original prompt")
            values = [
                str(r.get("value", "")) for r in group.select('input[type="radio"]')
            ]
            if [comparable(v) for v in values] != [
                comparable(v) for v in question["options"]
            ]:
                raise ValueError("Radio options disagree with original")
            raw = group.get("data-answers")
            if not isinstance(raw, str) or json.loads(raw) != [
                values[question["answer_index"]]
            ]:
                raise ValueError("Radio key disagrees with original")
        return source, 0
    fields = doc.select("select[data-answers]")
    if len(fields) != len(questions):
        raise ValueError("Original questions do not match local controls")
    replacements = []
    changed_prompts = 0
    corrected_answers = False
    for field, question in zip(fields, questions, strict=True):
        options = [o for o in field.select("option") if o.get("value") != ""]
        values = [str(o.get("value", o.get_text())) for o in options]
        if len(options) != len(question["options"]):
            raise ValueError("Original options do not match local control")
        raw_answers = field.get("data-answers")
        if not isinstance(raw_answers, str):
            raise ValueError("Local answer JSON must be a string")
        answers = json.loads(raw_answers)
        selected = question["answer_index"]
        if len(answers) != 1 or comparable(answers[0]) != comparable(values[selected]):
            raise ValueError("Local answer position disagrees with original key")
        label = field.find_parent("label")
        if label is None:
            raise ValueError("Local control has no label")
        label_copy = BeautifulSoup(str(label), "html.parser")
        for control in label_copy.select("select"):
            control.decompose()
        local_prompt = re.sub(r"^\d+\.\s*", "", label_copy.get_text(" ", strip=True))
        prompt_changed = bool(question["prompt"]) and comparable(
            local_prompt
        ) != comparable(question["prompt"])
        options_changed = any(
            comparable(old) != comparable(new)
            for old, new in zip(values, question["options"], strict=True)
        )
        if not prompt_changed and not options_changed:
            continue
        identifier = str(field.get("id", ""))
        if not identifier:
            raise ValueError("Local control has no id")
        if options_changed:
            for option, value in zip(options, question["options"], strict=True):
                option.string = value
                if option.has_attr("value"):
                    option["value"] = value
            field["data-answers"] = json.dumps(
                [question["options"][selected]], ensure_ascii=False
            )
            corrected_answers = True
        field["lang"] = "hu"
        for option in options:
            option["lang"] = "hu"
        if prompt_changed:
            label.clear()
            label["lang"] = "ro"
            label.append(f"{question['index'] + 1}. ")
            passage = doc.new_tag("span", lang="hu")
            passage.string = question["prompt"]
            label.append(passage)
            label.append(doc.new_tag("br"))
            label.append(field)
            changed_prompts += 1
        pattern = re.compile(
            r'<label\b[^>]*\bfor="' + re.escape(identifier) + r'"[^>]*>.*?</label\s*>',
            re.S,
        )
        if len(pattern.findall(source)) != 1:
            raise ValueError(f"Ambiguous local label: {identifier}")
        replacements.append((pattern, serialize_html(label)))
    for pattern, replacement in replacements:
        source = pattern.sub(
            lambda _, replacement=replacement: replacement, source, count=1
        )
    if corrected_answers:
        updated = BeautifulSoup(source, "html.parser")
        answers = []
        for field in updated.select("select[data-answers]"):
            value = field.get("data-answers")
            if not isinstance(value, str):
                raise ValueError("Invalid answer JSON")
            answers.append(json.loads(value)[0])
        solutions = updated.select_one("details.solutions ol")
        if solutions is None:
            raise ValueError("Missing solution list")
        solutions.clear()
        for answer in answers:
            item = updated.new_tag("li", lang="hu")
            item.string = answer
            solutions.append(item)
        source = re.sub(
            r'(<details\b[^>]*class="solutions"[^>]*>.*?)(<ol>.*?</ol>)',
            lambda m: m[1] + serialize_html(solutions),
            source,
            count=1,
            flags=re.S,
        )
    if replacements:
        instructions = [
            compact(td.get_text(" ", strip=True))
            for td in original_doc.select("td")
            if not td.find("input")
            and re.match(r"^(Care|Cu care|Alege)", compact(td.get_text()))
        ]
        if instructions:
            note = '<p class="note" lang="ro">' + html.escape(instructions[0]) + "</p>"
            # These legacy quiz intros contain only title/instructions/attribution.
            match = re.search(
                r'(<div class="lesson-content">)(.*?)(?=<p\b)', source, re.S
            )
            if match:
                intro = BeautifulSoup(match[2], "html.parser")
                if any(tag.name != "a" for tag in intro.find_all()):
                    return source, changed_prompts
                credit = intro.find("a")
                credit_html = (
                    (
                        '<p lang="ro">Creat după un model de la '
                        + serialize_html(credit)
                        + ".</p>"
                    )
                    if credit
                    else ""
                )
                source = (
                    source[: match.start(2)]
                    + note
                    + credit_html
                    + source[match.end(2) :]
                )
    return source, changed_prompts


def repair_site(root, sources, *, write=False):
    root, sources = Path(root).resolve(), Path(sources).resolve()
    records = json.loads((root / "assets/inventory.json").read_text(encoding="utf-8"))[
        "pages"
    ]
    updates = {}
    scanned = prompts = 0
    for record in records:
        if record["group"] != "exercitii":
            continue
        path = root / record["path"]
        if not path.resolve().is_relative_to(root):
            raise ValueError("Inventory path escapes site")
        original = decode_source((sources / path.name).read_bytes())
        source = path.read_text(encoding="utf-8")
        try:
            repaired, count = repair_page(source, original)
        except ValueError as error:
            raise ValueError(f"{record['path']}: {error}") from error
        scanned += 1
        if repaired != source:
            updates[path] = repaired
            prompts += count
    if write:
        for path, repaired in updates.items():
            path.write_text(repaired, encoding="utf-8")
    return {
        "scanned": scanned,
        "prompts": prompts,
        "pages": [p.relative_to(root).as_posix() for p in updates],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = repair_site(args.root, args.sources, write=args.write)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot repair prompts: {error}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result["pages"]) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
