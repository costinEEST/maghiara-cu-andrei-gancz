"""Repair legacy encoding and index activities by their actual lesson links.

Default: read-only audit. Use --write to update HTML and inventory, then format,
refresh SEO and regenerate the offline inventory. Existing URLs never change.
"""

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]
GROUPS = {
    "lectii": "Primii pași",
    "andras": "Maghiara cu András",
    "gramatica": "Gramatică",
    "vocabular": "Vocabular",
    "comunicare": "Comunicare",
    "referinte": "Resurse",
}
# Verified against the original file_44et9h0/file_vuuw7po HTML (Windows-1250).
# These replacement characters cannot be recovered by reversing UTF-8 mojibake.
WORDS = {
    "Ink�bb": "Inkább",
    "v�rtam": "vártam",
    "m�g": "még",
    "Mi�rt": "Miért",
    "k�r": "kár",
    "tal�ltam": "találtam",
    "legal�bb": "legalább",
    "m�st": "mást",
    "Sz�nom-b�nom": "Szánom-bánom",
    "megnős�ltem": "megnősültem",
    "Sajn�lom": "Sajnálom",
    "Szerencs�tlens�gemre": "Szerencsétlenségemre",
    "K�r": "Kár",
    "tort�b�l": "tortából",
    "sz�vesen": "szívesen",
    "H�t": "Hát",
    "K�rem": "Kérem",
    "k�rd�s": "kérdés",
    "n�zzem": "nézzem",
    "k�peket": "képeket",
    "M�g": "Még",
    "k�rded": "kérded",
    "kifog�som": "kifogásom",
    "sz�ket": "széket",
    "kifog�sod": "kifogásod",
    "J�l": "Jól",
    "Szeretn�k": "Szeretnék",
    "bar�taimmal": "barátaimmal",
    "keresztrejtv�ny": "keresztrejtvény",
}


def repair_encoding(text):
    """Reverse only known malformed byte sequences; preserve valid diacritics."""
    replacements = {}
    for char in "ăâîșțĂÂÎȘȚáéíóöőúüűÁÉÍÓÖŐÚÜŰ\u2013—„”":
        for encoding in ("latin1", "cp1252"):
            try:
                malformed = char.encode("utf-8").decode(encoding)
            except UnicodeError:
                continue
            replacements[malformed] = char
    for _ in range(3):
        for bad in sorted(replacements, key=len, reverse=True):
            text = text.replace(bad, replacements[bad])
    for bad, good in WORDS.items():
        text = text.replace(bad, good)
    return text


def pad_numbers(text):
    return re.sub(
        r"\b([Ll]ecția|[Ee]xercițiul)\s+(\d+)\b",
        lambda match: (
            match[0]
            if match[2] == f"{int(match[2]):03d}"
            else f"{match[1]} {int(match[2]):03d}"
        ),
        text,
    )


def activity_title(title, path):
    title = repair_encoding(title)
    title = re.sub(
        r"^Leçon\s*(\d+)\s*,\s*exercice\s*(\d+)",
        r"Lecția \1, exercițiul \2",
        title,
        flags=re.I,
    )
    title = re.sub(r"^(\d+)\.?\s*,?\s*lecke,?\s*", r"Lecția \1, ", title)
    title = re.sub(r"(\d+)\.\s*gyakorlat", r"exercițiul \1", title)
    for old, new in {
        "keresztrejtvény": "rebus",
        "rejtett szó": "cuvinte ascunse",
        "teszt": "test",
        "A család": "familia",
        "ének": "cântec",
        "Nevessünk egy kicsit": "să râdem puțin",
    }.items():
        title = title.replace(old, new)
    title = re.sub(r"(Lecția \d+, )([0-9]+)$", r"\1exercițiul \2", title)
    title = pad_numbers(title)
    variant = re.search(r"-varianta-(\d+)\.html$", path)
    if variant and not re.search(r" · [Vv]arianta \d+$", title):
        title += f" · Varianta {int(variant[1]):03d}"
    return title


def associations(pages, documents, index):
    """Use direct links, not filename guesses; preserve all shared parents."""
    records = {record["path"]: record for record in pages}
    if len(records) != len(pages):
        raise ValueError("Duplicate inventory paths")
    appearance = {
        anchor.get("href"): position
        for position, anchor in enumerate(index.select("[data-entry] > a[href]"))
    }
    parents = sorted(
        (record for record in pages if record["group"] != "exercitii"),
        key=lambda record: (
            list(GROUPS).index(record["group"]),
            record.get("number") or appearance.get(record["path"], 9999),
            record["path"],
        ),
    )
    matches = {r["path"]: [] for r in pages if r["group"] == "exercitii"}
    for rank, parent in enumerate(parents):
        seen = set()
        for position, anchor in enumerate(
            documents[parent["path"]].select(".lesson-content a[href]")
        ):
            href = anchor.get("href")
            if not isinstance(href, str):
                continue
            parsed = urlsplit(urljoin("https://local.invalid/" + parent["path"], href))
            if parsed.netloc != "local.invalid":
                continue
            target = unquote(parsed.path).lstrip("/")
            if target.startswith("exercitii/") and target.endswith(".html"):
                if target not in matches:
                    raise ValueError(f"{parent['path']}: unknown activity {target}")
                if target not in seen:
                    matches[target].append(
                        {
                            "path": parent["path"],
                            "position": position,
                            "parent_order": rank,
                        }
                    )
                    seen.add(target)
    missing = [path for path, links in matches.items() if not links]
    if missing:
        raise ValueError(f"Activities without a parent: {missing}")
    return matches


def parent_label(record):
    label = GROUPS[record["group"]]
    if record.get("number"):
        return f"{label} · Lecția {record['number']:03d}"
    return f"{label} · {record['title']}"


def display_key(record, records):
    """Order this index by lesson, including activities linked only by a topic.

    A title's lesson number is a display hint, never a new parent association.
    Keep stored activity IDs and individual page headings unchanged.
    """
    parent = records[record["primary_parent"]]
    lesson = re.match(r"Lecția (\d+)\b", record["title"])
    number = int(lesson[1]) if lesson else parent.get("number")
    if not number:
        return (1, 0, 0, 0, 0, record["catalog_number"])
    course = parent["group"] if parent.get("number") else "andras"
    exercise = re.search(r"\b(exercițiul|testul)\s+(\d+)", record["title"])
    kind = 0 if exercise and exercise[1] == "exercițiul" else 1 if exercise else 2
    return (
        0,
        list(GROUPS).index(course),
        number,
        kind,
        int(exercise[2]) if exercise else 0,
        record["catalog_number"],
    )


def context_labels(record, records):
    labels = []
    lesson = re.match(r"Lecția (\d+)\b", record["title"])
    for link in record["parents"]:
        parent = records[link["path"]]
        if lesson and parent.get("number") == int(lesson[1]):
            labels.append(GROUPS[parent["group"]])
        else:
            labels.append(parent_label(parent))
    return labels


def row_signature(row):
    def compact(text):
        return re.sub(r"\s+", " ", text).strip()

    return (
        row.get("data-order"),
        row.get("data-search"),
        len(row.select("br")),
        [
            (a.get("href"), compact(a.get_text(" ", strip=True)))
            for a in row.select("a")
        ],
        [
            (span.get("class"), compact(span.get_text(" ", strip=True)))
            for span in row.select("span")
        ],
    )


def index_catalog(root=ROOT, *, write=False):
    root = Path(root).resolve()
    inventory_path = root / "assets/inventory.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    before_inventory = json.dumps(inventory, ensure_ascii=False, sort_keys=True)
    pages = inventory["pages"]
    paths = ["index.html", "referinte/despre-editie.html"] + [r["path"] for r in pages]
    sources = {}
    originals = {}
    documents = {}
    for relative in paths:
        path = root / relative
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Path escapes site: {relative}")
        original = path.read_text(encoding="utf-8")
        source = pad_numbers(repair_encoding(original))
        if relative == "exercitii/permisiune-1.html":
            source = source.replace("�", "\u2013")
        if "�" in source:
            raise ValueError(f"Unresolved replacement character: {relative}")
        doc = BeautifulSoup(source, "html.parser")
        if doc.head is None or doc.h1 is None:
            raise ValueError(f"Missing head or h1: {relative}")
        sources[relative], originals[relative], documents[relative] = (
            source,
            original,
            doc,
        )
    index = documents["index.html"]
    section = index.select_one("#activitati")
    listing = section.select_one("ol.catalog-list") if section else None
    if listing is None:
        raise ValueError("Missing activity catalog")
    matches = associations(pages, documents, index)
    records = {r["path"]: r for r in pages}
    ordered = sorted(
        matches,
        key=lambda path: (
            matches[path][0]["parent_order"],
            matches[path][0]["position"],
            path,
        ),
    )
    for record in pages:
        record["title"] = pad_numbers(repair_encoding(record["title"]))
    for number, relative in enumerate(ordered, 1):
        record = records[relative]
        record["title"] = activity_title(record["title"], relative)
        parent = records[matches[relative][0]["path"]]
        lesson = re.match(r"Lecția (\d+)", record["title"])
        if lesson and parent.get("number") and int(lesson[1]) != parent["number"]:
            record.setdefault("source_title", record["title"])
            record["title"] = re.sub(
                r"^Lecția \d+", f"Lecția {parent['number']:03d}", record["title"]
            )
        record["catalog_number"] = number
        record["parents"] = matches[relative]
        record["primary_parent"] = matches[relative][0]["path"]
        heading = f"Activitatea {number:03d} — {record['title']}"
        sources[relative] = re.sub(
            r"<h1\b[^>]*>.*?</h1>",
            lambda _, heading=heading: f'<h1 lang="ro">{html.escape(heading)}</h1>',
            sources[relative],
            count=1,
            flags=re.S,
        )
    # Only replace the catalog when semantic content changes. A formatter's
    # whitespace never makes a subsequent read-only audit fail.
    desired = []
    display_order = sorted(
        ordered, key=lambda path: display_key(records[path], records)
    )
    for number, relative in enumerate(display_order, 1):
        record = records[relative]
        labels = [parent_label(records[p["path"]]) for p in matches[relative]]
        context = context_labels(record, records)
        search = html.escape(record["title"] + " " + " ".join(labels), quote=True)
        row_doc = BeautifulSoup(
            f'<li data-entry="" data-order="{number}" '
            f'data-search="{search}">'
            f'<a href="{relative}"><span class="item-number">{number:03d}</span>'
            f'<span class="activity-title">{html.escape(record["title"])}<br>'
            f'<small class="activity-context">{html.escape("; ".join(context))}</small>'
            '</span><span class="item-label">Citește</span></a></li>',
            "html.parser",
        )
        row = row_doc.li
        assert row is not None
        desired.append(row)
    current = listing.find_all("li", recursive=False)
    if listing.get("role") != "list" or [row_signature(r) for r in current] != [
        row_signature(r) for r in desired
    ]:
        listing["role"] = "list"
        listing.clear()
        for row in desired:
            listing.append(row)
        original_section = re.search(
            r'<section\b[^>]*\bid="activitati"[^>]*>.*?</section>',
            sources["index.html"],
            flags=re.S,
        )
        if original_section is None:
            raise ValueError("Missing activity section source")
        sources["index.html"] = sources["index.html"].replace(
            original_section[0], serialize_html(section), 1
        )
    # Course badges are padded too; their order is explicit numeric lesson order.
    sources["index.html"] = re.sub(
        r'(<span class="item-number">)(\d{1,2})(</span\s*>)',
        lambda m: f"{m[1]}{int(m[2]):03d}{m[3]}",
        sources["index.html"],
    )
    changed = [p for p in paths if sources[p] != originals[p]]
    inventory_changed = before_inventory != json.dumps(
        inventory, ensure_ascii=False, sort_keys=True
    )
    if write:
        for relative in changed:
            (root / relative).write_text(sources[relative], encoding="utf-8")
        if inventory_changed:
            inventory_path.write_text(
                json.dumps(inventory, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return {
        "activities": len(ordered),
        "shared": sum(len(v) > 1 for v in matches.values()),
        "changed": changed,
        "inventory_changed": inventory_changed,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--write", action="store_true", help="Apply after all inputs validate"
    )
    parser.add_argument(
        "--check", action="store_true", help="Read-only audit (default)"
    )
    args = parser.parse_args(argv)
    if args.write and args.check:
        parser.error("Use either --write or --check")
    try:
        result = index_catalog(args.root, write=args.write)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Catalog audit failed: {error}\n")
    print(
        f"Activities: {result['activities']}; shared parents: {result['shared']}; "
        f"HTML changes: {len(result['changed'])}; "
        f"inventory change: {result['inventory_changed']}"
    )
    return int(
        not args.write and bool(result["changed"] or result["inventory_changed"])
    )


if __name__ == "__main__":
    raise SystemExit(main())
