#!/usr/bin/env python3
"""Apply conservative language labels using the edition's bilingual alignment.

This is a markup aid, not a language detector. Romanian is the document default.
It uses the explicitly Hungarian vocabulary/answer corpus and aligned table
cells, leaving uncertain prose alone for editorial review. Text is never changed.
"""

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup, Comment, NavigableString

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]


def label_languages(root=ROOT):
    """Process an explicit site root; importing this module never changes files."""
    root = Path(root).resolve()
    inventory = json.loads((root / "assets/inventory.json").read_text(encoding="utf-8"))
    records = {r["path"]: r for r in inventory["pages"]}
    if len(records) != len(inventory["pages"]):
        raise ValueError("Duplicate inventory paths")
    paths = [root / "index.html", root / "referinte/despre-editie.html"] + [
        root / p for p in records
    ]
    if any(not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("Inventory path escapes site")
    docs = {
        p: BeautifulSoup(p.read_text(encoding="utf-8"), "html.parser") for p in paths
    }
    for path, doc in docs.items():
        if doc.html is None:
            raise ValueError(f"{path}: missing html element")
    romanian = set(
        [
            "acest",
            "aceasta",
            "aceste",
            "acestea",
            "acel",
            "acea",
            "acele",
            "cei",
            "cele",
            "ceea",
            "care",
            "dintre",
            "este",
            "sunt",
            "suntem",
            "sunteți",
            "sunteţi",
            "pentru",
            "prin",
            "din",
            "sau",
            "dacă",
            "deci",
            "deoarece",
            "astfel",
            "numai",
            "persoana",
            "verbul",
            "verbele",
            "substantivul",
            "pronumele",
            "articolul",
            "exemplu",
            "exemple",
            "explicații",
            "explicaţii",
            "exerciții",
            "exerciţii",
            "cuvinte",
            "cuvântul",
            "forme",
            "forma",
            "limba",
            "maghiară",
            "română",
            "singular",
            "plural",
            "prezent",
            "trecut",
            "indicativ",
            "verb",
            "substantiv",
            "feminin",
            "masculin",
            "neutru",
            "familia",
            "adjectiv",
            "adverb",
            "conjuncție",
            "pronume",
            "complement",
            "enunțuri",
            "exprima",
            "exprimarea",
            "ordinea",
            "puneți",
            "completați",
            "alegeți",
            "răspunsul",
            "reține",
            "rețineți",
            "vezi",
            "primul",
            "prima",
            "ultimul",
            "unui",
            "unei",
            "niște",
            "fiecare",
            "cum",
            "când",
            "cu",
            "unde",
            "cine",
            "ce",
            "tot",
            "dar",
            "meu",
            "mea",
            "ta",
            "tu",
            "eu",
            "el",
            "ea",
            "da",
            "nu",
            "noi",
            "voi",
            "ei",
            "ele",
            "aici",
            "acolo",
            "nimic",
            "ceva",
            "bine",
            "foarte",
            "introducere",
            "salut",
            "comunicare",
            "sens",
            "literă",
            "litere",
            "scurt",
            "lung",
            "vocale",
            "consoane",
            "învățăm",
            "observăm",
        ]
    )
    ro_answers = {"da", "nu", "fără continuare"}

    def compact(value):
        return re.sub(r"\s+", " ", value).strip()

    def words(value):
        return re.findall(r"[^\W\d_]+", value.lower(), re.UNICODE)

    def ro_evidence(value):
        return (
            bool(re.search("[ăâîșțşţ]", value, re.I))
            or any(
                w in romanian
                for w in words(value)
                if len(w) > 2
                or w in ["ce", "cu", "nu", "eu", "ei", "ea", "un", "tu", "noi", "voi"]
            )
            or any(
                w in ["spune", "toate", "acum", "acestei", "acestea"]
                for w in words(value)
            )
        )

    vocabulary = set(
        [
            "szia",
            "szervusz",
            "sziasztok",
            "szervusztok",
            "szevasz",
            "köszönöm",
            "kösz",
            "köszi",
            "viszlát",
            "igen",
            "nem",
            "jó",
            "jól",
            "hogy",
            "vagy",
            "vagyok",
            "vagyunk",
            "vagytok",
            "van",
            "vannak",
            "nincs",
            "nincsenek",
            "egy",
            "az",
            "ez",
            "én",
            "te",
            "ő",
            "mi",
            "ti",
            "ők",
            "ön",
            "önök",
            "maga",
            "maguk",
            "ki",
            "mit",
            "és",
            "is",
            "szép",
            "könyv",
            "alma",
            "körte",
            "magyar",
            "magyarul",
            "román",
            "románul",
            "beszél",
            "beszélek",
            "első",
            "második",
            "harmadik",
            "lecke",
            "bevezető",
            "magyarázatok",
            "gyakorlatok",
            "szókincs",
            "ismétlés",
            "nyelvtan",
            "kommunikáció",
            "bemutatkozás",
            "szövegértés",
            "kakukktojás",
        ]
    )
    for path, doc in docs.items():
        for node in doc.select("[lang=hu]"):
            if records.get(path.relative_to(root).as_posix(), {}).get(
                "group"
            ) != "vocabular" and not node.find_parent(class_="solutions"):
                continue
            if (
                records.get(path.relative_to(root).as_posix(), {}).get("group")
                == "vocabular"
                and node.name != "span"
            ):
                continue
            if node.name in ["input", "select", "textarea"]:
                continue
            value = compact(node.get_text())
            if value.lower() not in ro_answers and not ro_evidence(value):
                vocabulary.update(words(value))
        for field in doc.select("[data-answers]"):
            raw_answers = field.get("data-answers")
            if not isinstance(raw_answers, str):
                raise ValueError(f"{path}: data-answers must be a JSON string")
            answers = json.loads(raw_answers)
            if not isinstance(answers, list) or any(
                not isinstance(answer, str) for answer in answers
            ):
                raise ValueError(f"{path}: data-answers must contain a list of strings")
            for value in answers:
                if value.lower() not in ro_answers and not ro_evidence(value):
                    vocabulary.update(words(value))

    def hungarian(value):
        value = compact(value)
        tokens = words(value)
        if not tokens or ro_evidence(value) or value.lower() in ro_answers:
            return False
        if any(
            w in ["translate", "google", "youtube", "http", "https", "www", "audio"]
            for w in tokens
        ):
            return False
        hits = sum(w in vocabulary for w in tokens)
        if len(tokens) == 1:
            return tokens[0] in vocabulary or bool(re.search("[őű]", value, re.I))
        return hits / len(tokens) >= 0.65 or (
            bool(re.search("[őű]", value, re.I))
            and (hits / len(tokens) >= 0.2 or len(tokens) <= 3)
        )

    def inherited(node):
        if getattr(node, "get", None) and node.get("lang"):
            return node["lang"]
        parent = node.find_parent(attrs={"lang": True})
        return parent.get("lang") if parent else "ro"

    counts = Counter()
    review = []
    for path, doc in docs.items():
        relative = path.relative_to(root).as_posix()
        group = records.get(relative, {}).get("group")
        html = doc.html
        assert html is not None  # All documents were checked before any writes.
        html["lang"] = "ro"
        # Correct existing over-broad labels on Romanian answers and option prompts.
        for node in doc.select("[lang=hu]"):
            if (
                node.name not in ["input", "textarea"]
                and compact(node.get_text()).lower() in ro_answers
            ):
                node["lang"] = "ro"
        for select in doc.select("select"):
            if select.get("lang") == "hu":
                select["lang"] = "ro"
            for option in select.select("option"):
                value = compact(option.get_text())
                option["lang"] = (
                    "ro"
                    if not option.get("value", value)
                    or value.lower() in ro_answers
                    or ro_evidence(value)
                    else "hu"
                    if hungarian(value)
                    else "ro"
                )
        # Bilingual headings and links retain a Romanian outer container.
        for node in list(
            doc.select(
                "h1,h2,h3,.catalog-list a>span:not([class]),"
                ".page-toc a,.pager a,.article-header>a"
            )
        ):
            if inherited(node) == "hu":
                continue
            if node.find("span", attrs={"lang": "hu"}):
                continue
            for text in list(node.find_all(string=True)):
                parent = text.parent
                if (
                    isinstance(text, Comment)
                    or parent is None
                    or parent.name in ["script", "style"]
                ):
                    continue
                value = str(text)
                if " / " in value:
                    left, right = value.split(" / ", 1)
                    if hungarian(left):
                        span = doc.new_tag("span", lang="hu")
                        span.string = left
                        text.replace_with(span)
                        span.insert_after(NavigableString(" / " + right))
                        counts["bilingual_titles"] += 1
        content = doc.select_one(".lesson-content")
        if content:
            # Two/three-column dialogue and phrase rows: only the Hungarian cell.
            for row in content.select("tr"):
                cells = row.find_all(["td", "th"], recursive=False)
                if len(cells) < 2:
                    continue
                for cell in cells:
                    value = compact(cell.get_text())
                    other = [compact(c.get_text()) for c in cells if c is not cell]
                    if (
                        value
                        and hungarian(value)
                        and not cell.find(["table", "input", "select"])
                        and (
                            any(ro_evidence(t) for t in other)
                            or group in ["lectii", "andras", "comunicare", "gramatica"]
                        )
                    ):
                        cell["lang"] = "hu"
                        counts["table_cells"] += 1
            # Hungarian examples in Romanian explanation text are usually emphasized.
            for node in content.select("em,i,b,strong"):
                if inherited(node) == "hu":
                    continue
                value = compact(node.get_text())
                if hungarian(value):
                    node["lang"] = "hu"
                    counts["inline_examples"] += 1
            # Plain Hungarian dialogue paragraphs and exercise prompts.
            for node in content.select("p,label"):
                if inherited(node) == "hu":
                    continue
                clone = BeautifulSoup(str(node), "html.parser")
                for field in clone.select("select,input,textarea,.answer-result"):
                    field.decompose()
                value = compact(clone.get_text())
                if hungarian(value) and not node.find(["table", "select", "input"]):
                    node["lang"] = "hu"
                    counts["paragraphs"] += 1
            # Text adjoining an input remains separately marked; controls and labels
            # keep their own language, rather than changing a mixed parent cell.
            for node in list(content.find_all(string=True)):
                parent = node.parent
                if isinstance(node, Comment) or parent is None:
                    continue
                if inherited(node) == "hu" or parent.name in [
                    "script",
                    "style",
                    "option",
                    "summary",
                    "button",
                ]:
                    continue
                if node.find_parent(["button", "summary"]) or node.find_parent(
                    class_="note"
                ):
                    continue
                value = compact(str(node))
                if hungarian(value) and (
                    len(words(value)) >= 2 or re.search("[őűŐŰ]", value)
                ):
                    span = doc.new_tag("span", lang="hu")
                    node.replace_with(span)
                    span.append(node)
                    counts["text_passages"] += 1
                elif re.search("[őűŐŰ]", value):
                    pieces = re.split(r"([^\W\d_]*[őűŐŰ][^\W\d_]*)", str(node))
                    if len(pieces) > 1:
                        container = doc.new_tag("span")
                        for piece in pieces:
                            if re.search("[őűŐŰ]", piece):
                                part = doc.new_tag("span", lang="hu")
                                part.string = piece
                                container.append(part)
                            else:
                                container.append(NavigableString(piece))
                        node.replace_with(container)
                        counts["inline_words"] += 1
            for link in content.select("a"):
                if compact(link.get_text()) == "Le hongrois avec András":
                    link["lang"] = "fr"
            for node in list(content.select(".note")):
                for text in list(node.find_all(string=True)):
                    if inherited(text) == "hu":
                        continue
                    pieces = re.split(
                        r"((?<!\w)-[a-záéíóöőúüű]+(?:/-?[a-záéíóöőúüű]+)*)",
                        str(text),
                        flags=re.I,
                    )
                    if len(pieces) > 1:
                        container = doc.new_tag("span")
                        for i, piece in enumerate(pieces):
                            if i % 2:
                                suffix = doc.new_tag("span", lang="hu")
                                suffix.string = piece
                                container.append(suffix)
                            else:
                                container.append(NavigableString(piece))
                        text.replace_with(container)
                        counts["instruction_suffixes"] += 1
            for node in content.select("em,i"):
                if inherited(node) == "hu" and re.match(
                    r"^(subst\.|adj\.|adv\.|verb\b|fam\.|lit\.|literal\b|termen\b)",
                    compact(node.get_text()),
                    re.I,
                ):
                    node["lang"] = "ro"
            # Residual distinctive Hungarian spellings warrant human review, not a
            # blanket language attribute on the surrounding Romanian explanation.
            for node in content.find_all(string=True):
                parent = node.parent
                if isinstance(node, Comment) or parent is None:
                    continue
                if (
                    inherited(node) != "hu"
                    and re.search("[őűŐŰ]", str(node))
                    and parent.name not in ["script", "style"]
                ):
                    review.append({"page": relative, "text": compact(str(node))[:240]})
        # Make implicit labels explicit without changing text or layout.
        for i, label in enumerate(doc.select("label")):
            control = label.find(["input", "select", "textarea"])
            if control:
                if not control.get("id"):
                    control["id"] = f"raspuns-{i + 1}"
                label["for"] = control["id"]
        path.write_text(serialize_html(doc), encoding="utf-8")
    report = {
        "labels_added": dict(counts),
        "remaining_distinctive_hungarian_passages": review,
        "note": (
            "Conservative labels based on source alignment and vocabulary. "
            "Mixed unstyled prose still needs editorial review; "
            "no full linguistic certification is claimed."
        ),
    }
    audit_path = root / "tools/language-audit.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Site directory")
    args = parser.parse_args(argv)
    try:
        result = label_languages(args.root)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot label site languages: {error}\n")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
