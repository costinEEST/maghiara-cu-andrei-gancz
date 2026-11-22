#!/usr/bin/env python3
"""Update static metadata and sitemap from the maintained HTML and site-config.json.
Does not generate lesson content or require the original submission archives.
Run from any directory: python3 tools/prepare_seo.py
"""

import argparse
import json
import re
from collections import Counter
from contextlib import suppress
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from xml.sax.saxutils import escape

from bs4 import BeautifulSoup

from html_attributes import serialize_html

ROOT = Path(__file__).resolve().parents[1]


def head_signature(head):
    """Compare metadata values independently of formatting and element order."""
    values = []
    for node in head.find_all(recursive=False):
        content = str(node.string or "").strip()
        if node.get("type") == "application/ld+json":
            with suppress(ValueError):
                content = json.dumps(
                    json.loads(content), ensure_ascii=False, sort_keys=True
                )
        values.append((node.name, json.dumps(node.attrs, sort_keys=True), content))
    return sorted(values)


def meta(doc, key, value, attr="name"):
    head = doc.head
    nodes = head.find_all("meta", attrs={attr: key})
    node = nodes[0] if nodes else doc.new_tag("meta", attrs={attr: key})
    for duplicate in nodes[1:]:
        duplicate.decompose()
    node["content"] = value
    if not nodes:
        head.append(node)


def prepare_seo(root=ROOT):
    """Process an explicit site root; importing this module never changes files."""
    root = Path(root).resolve()
    CONFIG = json.loads((root / "site-config.json").read_text(encoding="utf-8"))
    BASE = CONFIG["public_url"].rstrip("/") + "/"
    parsed_base = urlsplit(BASE)
    if (
        parsed_base.scheme != "https"
        or not parsed_base.netloc
        or parsed_base.query
        or parsed_base.fragment
    ):
        raise ValueError("site-config.json public_url must be an absolute HTTPS URL")
    GROUPS = {
        "lectii": "Primii pași",
        "andras": "Maghiara cu András",
        "gramatica": "Gramatică",
        "vocabular": "Vocabular",
        "comunicare": "Comunicare",
        "referinte": "Resurse",
        "exercitii": "Exerciții și lecturi",
    }
    LICENSE = "https://creativecommons.org/licenses/by-sa/3.0/ro/"
    inventory = json.loads((root / "assets/inventory.json").read_text(encoding="utf-8"))
    records = {r["path"]: r for r in inventory["pages"]}
    if len(records) != len(inventory["pages"]):
        raise ValueError("Duplicate inventory paths")
    paths = [root / "index.html", root / "referinte/despre-editie.html"] + [
        root / p for p in records
    ]
    if any(not path.resolve().is_relative_to(root) for path in paths):
        raise ValueError("Inventory path escapes site")
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate inventory paths")
    titles, descriptions, urls = [], [], []
    rendered = {}

    def compact(value):
        return re.sub(r"\s+", " ", value).strip()

    for path in paths:
        relative = path.relative_to(root).as_posix()
        record = records.get(relative, {})
        doc = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        if doc.head is None or doc.title is None or doc.h1 is None:
            raise ValueError(f"{relative}: missing head, title or h1")
        original_head = head_signature(doc.head)
        heading = compact(doc.h1.get_text(" ", strip=True))
        topic = heading.split(" / ")[-1]
        group = record.get("group", "referinte")
        number = record.get("number")
        variant = re.search(r"-varianta-(\d+)\.html$", relative)
        if variant and not re.search(r" · [Vv]arianta \d+$", topic):
            topic += f" · varianta {variant[1]}"
        if group == "exercitii" and record.get("catalog_number"):
            topic = f"Activitatea {record['catalog_number']:03d} — {record['title']}"
        label = GROUPS[group]
        if relative == "index.html":
            title = "Învață maghiara: lecții, vocabular și gramatică | Nebuló"
            description = (
                "Învață limba maghiară în română: 50 de lecții, dialoguri cu audio, "
                "vocabular tematic, gramatică și exerciții cu răspunsuri. "
                "Parcurge cursul în ritmul tău."
            )
        else:
            title = (f"Lecția {number:03d}: " if number else "") + topic
            if group == "andras":
                title += " | András"
            elif group in ("gramatica", "vocabular", "comunicare"):
                title += " | " + label
            title += " | Nebuló"
            prefix = (
                f"Lecția {number:03d} din cursul {label}: "
                if number
                else label + " în limba maghiară: "
            )
            if group == "exercitii":
                description = (
                    topic + ". Exersează limba maghiară cu activități și lecturi, "
                    "apoi revino la lecția asociată pentru explicații în română."
                )
            elif group == "referinte":
                description = (
                    topic + ". Îndrumări și resurse pentru a învăța limba maghiară "
                    "în română, cu trimiteri la materialele originale Nebuló."
                )
            else:
                description = (
                    prefix
                    + topic
                    + ". Citește exemplele maghiare și explicațiile în română. "
                    "Învață pas cu pas, în ritmul tău."
                )
        # Shorten long snippets at a word boundary.
        if len(description) > 185:
            description = description[:182].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
        canonical = BASE if relative == "index.html" else urljoin(BASE, relative)
        titles.append(title)
        descriptions.append(description)
        urls.append(canonical)
        doc.title.string = title
        head = doc.head
        if (root / "manifest.webmanifest").is_file():
            prefix = "" if relative == "index.html" else "../"
            for old in head.select('link[rel="manifest"],link[rel="apple-touch-icon"]'):
                old.decompose()
            head.append(
                doc.new_tag(
                    "link", rel="manifest", href=prefix + "manifest.webmanifest"
                )
            )
            head.append(
                doc.new_tag(
                    "link",
                    rel="apple-touch-icon",
                    href=prefix + "assets/pwa/apple-touch-icon.png",
                )
            )
            if not head.find("script", src=prefix + "assets/pwa.js"):
                head.append(
                    doc.new_tag("script", src=prefix + "assets/pwa.js", defer="")
                )
        for old in head.select("link[rel=icon]"):
            old.decompose()
        head.append(
            doc.new_tag(
                "link",
                rel="icon",
                type="image/svg+xml",
                href=("" if relative == "index.html" else "../") + "assets/favicon.svg",
            )
        )

        meta(doc, "description", description)
        meta(doc, "robots", "index, follow, max-image-preview:large")
        meta(doc, "theme-color", "#24634c")
        for obsolete in head.select(
            "meta[name=keywords],meta[http-equiv=content-language]"
        ):
            obsolete.decompose()
        for old in head.select("link[rel=canonical]"):
            old.decompose()
        head.append(doc.new_tag("link", rel="canonical", href=canonical))
        values = {
            "type": "website",
            "locale": CONFIG["locale"],
            "site_name": CONFIG["site_name"],
            "title": title,
            "description": description,
            "url": canonical,
            "image": urljoin(BASE, CONFIG["social_image"]),
            "image:type": "image/png",
            "image:width": "1200",
            "image:height": "630",
            "image:alt": (
                "Nebuló — Învață maghiara, pas cu pas. "
                "Lecții și resurse pentru vorbitori de română."
            ),
        }
        for name, value in values.items():
            meta(doc, "og:" + name, value, "property")
        for name, value in {
            "card": "summary_large_image",
            "title": title,
            "description": description,
            "image": values["image"],
            "image:alt": values["image:alt"],
        }.items():
            meta(doc, "twitter:" + name, value)
        for old in head.select("script[data-site-schema]"):
            old.decompose()
        resource = {
            "@type": "CollectionPage"
            if relative == "index.html"
            else ["WebPage", "LearningResource"],
            "@id": canonical + "#page",
            "url": canonical,
            "name": title,
            "description": description,
            "inLanguage": ["ro", "hu"],
            "isAccessibleForFree": True,
            "license": LICENSE,
            "image": values["image"],
            "isPartOf": {"@id": BASE + "#website"},
        }
        if record:
            resource["isBasedOn"] = "https://www.nebulo.ro/" + record["old"]
            resource["learningResourceType"] = (
                "lecție"
                if number
                else "exercițiu sau lectură"
                if group == "exercitii"
                else "referință"
            )
            if group in ["andras", "gramatica", "vocabular", "comunicare"]:
                resource["author"] = {
                    "@type": "Person",
                    "name": "András (Andrei) Gancz",
                }
            elif group == "lectii":
                resource["author"] = {"@type": "Person", "name": "László Kozma"}
        graph = [resource]
        if relative == "index.html":
            graph.append(
                {
                    "@type": "WebSite",
                    "@id": BASE + "#website",
                    "url": BASE,
                    "name": CONFIG["site_name"],
                    "inLanguage": "ro",
                }
            )
        else:
            graph.append(
                {
                    "@type": "BreadcrumbList",
                    "itemListElement": [
                        {
                            "@type": "ListItem",
                            "position": 1,
                            "name": "Cuprins",
                            "item": BASE,
                        },
                        {
                            "@type": "ListItem",
                            "position": 2,
                            "name": label,
                            "item": BASE
                            + "#"
                            + ("activitati" if group == "exercitii" else group),
                        },
                        {
                            "@type": "ListItem",
                            "position": 3,
                            "name": heading,
                            "item": canonical,
                        },
                    ],
                }
            )
        schema = doc.new_tag(
            "script", type="application/ld+json", attrs={"data-site-schema": ""}
        )
        schema_json = json.dumps(
            {"@context": "https://schema.org", "@graph": graph},
            ensure_ascii=False,
            indent=2,
        )
        schema.string = (
            "\n"
            + "\n".join("      " + line for line in schema_json.splitlines())
            + "\n    "
        )
        head.append(schema)
        # Metadata updates must not reserialize lesson examples or inline words.
        original = path.read_text(encoding="utf-8")
        rendered[path] = original
        if original_head != head_signature(head):
            rendered[path] = re.sub(
                r"<head\b[^>]*>.*?</head>",
                lambda _, head=head: serialize_html(head),
                original,
                count=1,
                flags=re.S | re.I,
            )

    for label, values in [("titles", titles), ("descriptions", descriptions)]:
        duplicates = [value for value, count in Counter(values).items() if count > 1]
        if duplicates:
            raise ValueError(f"Duplicate {label}: {duplicates}")
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(
            "  <url>\n    <loc>" + escape(url) + "</loc>\n  </url>\n" for url in urls
        )
        + "</urlset>\n"
    )

    for path, source in rendered.items():
        path.write_text(source, encoding="utf-8")
    root.joinpath("sitemap.xml").write_text(sitemap, encoding="utf-8")
    return len(paths)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Site directory")
    args = parser.parse_args(argv)
    try:
        result = prepare_seo(args.root)
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
        parser.exit(1, f"Cannot prepare site SEO: {error}\n")
    print(f"Updated SEO metadata and sitemap for {result} pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
