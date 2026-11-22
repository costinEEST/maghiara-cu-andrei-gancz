"""Validate the maintained site without rewriting any files."""

import argparse
import json
import re
import struct
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def validate_document(doc, path, root, config, documents):
    """Report malformed page data rather than crashing on the first missing tag."""
    name = path.relative_to(root).as_posix()
    errors = []
    fields = 0

    def fail(message):
        errors.append(f"{name}: {message}")

    def metadata(selector):
        node = doc.select_one(selector)
        return node.get("content", "") if node else ""

    base = config["public_url"].rstrip("/") + "/"
    expected = base if name == "index.html" else urljoin(base, name)
    if len(doc.select("h1")) != 1:
        fail("Expected exactly one h1")
    if len(doc.select("main")) != 1:
        fail("Expected exactly one main")
    if doc.html is None or doc.html.get("lang") != "ro":
        fail("Missing document language")
    if not doc.select_one("meta[name=viewport]"):
        fail("Missing viewport")
    title = doc.title.get_text(strip=True) if doc.title else ""
    description = metadata("meta[name=description]")
    if not title or not description:
        fail("Missing SEO title/description")
    canonical = doc.select_one("link[rel=canonical]")
    if not canonical or canonical.get("href") != expected:
        fail("Incorrect canonical URL")
    for prop in (
        "title",
        "description",
        "type",
        "url",
        "locale",
        "site_name",
        "image",
        "image:width",
        "image:height",
        "image:alt",
    ):
        if not metadata(f'meta[property="og:{prop}"]'):
            fail("Missing Open Graph " + prop)
    if metadata('meta[property="og:url"]') != expected:
        fail("Canonical/Open Graph mismatch")
    if metadata('meta[property="og:image"]') != urljoin(base, config["social_image"]):
        fail("Incorrect social image")
    if not doc.select_one('meta[name="twitter:card"][content="summary_large_image"]'):
        fail("Missing social card")
    try:
        script = doc.select_one("script[data-site-schema]")
        schema = json.loads(script.get_text() if script else "")
        graph = schema.get("@graph") if isinstance(schema, dict) else None
        if not isinstance(graph, list) or not graph or not isinstance(graph[0], dict):
            fail("Invalid JSON-LD graph")
        elif graph[0].get("url") != expected:
            fail("Incorrect schema URL")
    except (TypeError, ValueError):
        fail("Invalid JSON-LD")
    ids = Counter(node["id"] for node in doc.select("[id]"))
    duplicates = [key for key, count in ids.items() if count > 1]
    if duplicates:
        fail("Duplicate IDs: " + str(duplicates))
    for node in doc.find_all(True):
        if any(attribute.startswith("on") for attribute in node.attrs):
            fail("Legacy inline event handler")
    for node in doc.select(
        "a[href],img[src],source[src],audio[src],script[src],link[href]"
    ):
        url = node.get("href", node.get("src", ""))
        try:
            parsed = urlsplit(url)
        except ValueError:
            fail("Malformed URL: " + url)
            continue
        if parsed.scheme or parsed.netloc:
            if parsed.scheme == "javascript":
                fail("javascript link")
            if node.name in ("img", "source", "script", "audio"):
                fail("Remote asset: " + url)
            if "forum" in url.lower():
                fail("Forum link")
            continue
        if parsed.path.startswith("/"):
            dest = (root / unquote(parsed.path).lstrip("/")).resolve()
        else:
            dest = (
                (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
            )
        if not dest.is_relative_to(root):
            fail("Link outside edition: " + url)
        elif not dest.is_file():
            fail("Missing file: " + url)
        elif parsed.fragment and dest in documents:
            fragment = unquote(parsed.fragment).split(":~:text=", 1)[0]
            if fragment and not documents[dest].find(id=fragment):
                fail("Missing fragment: " + url)
    for image in doc.select("img"):
        if "alt" not in image.attrs:
            fail("Image without alternative")
    for control in doc.select("input:not([type=button]),select,textarea"):
        control_id = control.get("id")
        if not (
            control.get("aria-label")
            or control.find_parent("label")
            or (control_id and doc.find("label", attrs={"for": control_id}))
        ):
            fail("Unlabelled control")
    for field in doc.select("[data-answers]"):
        fields += 1
        try:
            answers = json.loads(field["data-answers"])
        except (TypeError, ValueError):
            fail("Invalid answer JSON")
            continue
        if (
            not isinstance(answers, list)
            or not answers
            or any(
                not isinstance(answer, str) or not answer.strip() for answer in answers
            )
        ):
            fail("Empty or invalid answer key")
            continue
        if field.name == "select":
            options = {
                " ".join(option.get("value", option.get_text()).split())
                for option in field.select("option")
            }
            if not all(" ".join(answer.split()) in options for answer in answers):
                fail("Answer missing from select options")
        if field.name == "fieldset" and field.has_attr("data-choice"):
            legend = field.find("legend", recursive=False)
            radios = field.select('input[type="radio"]')
            values = {str(radio.get("value", "")) for radio in radios}
            names = {str(radio.get("name", "")) for radio in radios}
            if legend is None or not legend.get_text(strip=True):
                fail("Radio question lacks a visible legend")
            if not 2 <= len(radios) <= 5 or len(values) != len(radios):
                fail("Invalid radio answer choices")
            if len(names) != 1 or "" in names:
                fail("Radio choices must share a nonempty group name")
            if not all(" ".join(answer.split()) in values for answer in answers):
                fail("Answer missing from radio choices")
            if any(radio.has_attr("checked") for radio in radios):
                fail("Radio exercise must start without a selected answer")
    for field in doc.select(".lesson-content input,.lesson-content select"):
        if re.fullmatch(r"Gap\d+", str(field.get("id", ""))) and not field.has_attr(
            "data-answers"
        ):
            fail("Missing cloze answer key")
    for disclosure in doc.select("details.solutions"):
        content = " ".join(
            child.get_text(" ", strip=True)
            for child in disclosure.find_all(recursive=False)
            if child.name != "summary"
        )
        if not content.strip():
            fail("Empty solutions disclosure")
    for region in doc.select(".table-scroll"):
        label = region.get("aria-label")
        named = isinstance(label, str) and bool(label.strip())
        labelledby = region.get("aria-labelledby")
        if isinstance(labelledby, str) and labelledby.split():
            targets = [doc.find(id=part) for part in labelledby.split()]
            named = named or all(
                target is not None and bool(target.get_text(strip=True))
                for target in targets
            )
        if region.get("tabindex") != "0" or not named:
            fail("Table region not named and keyboard focusable")
    return errors, fields, title, description, expected


def validate_site(root=ROOT):
    root = Path(root).resolve()
    report = {"errors": [], "pages": 0, "answer_fields": 0}
    errors = report["errors"]
    try:
        inventory = json.loads(
            (root / "assets/inventory.json").read_text(encoding="utf-8")
        )
        config = json.loads((root / "site-config.json").read_text(encoding="utf-8"))
        if not isinstance(config, dict) or any(
            not isinstance(config.get(key), str) or not config[key]
            for key in ("public_url", "social_image")
        ):
            raise ValueError("Missing public_url or social_image configuration")
        public_url = urlsplit(config["public_url"])
        if (
            public_url.scheme != "https"
            or not public_url.netloc
            or public_url.query
            or public_url.fragment
        ):
            raise ValueError("public_url must be an absolute HTTPS base URL")
        paths = [root / "index.html", root / "referinte/despre-editie.html"]
        for record in inventory["pages"]:
            relative = record["path"]
            path = (root / relative).resolve()
            if Path(relative).is_absolute() or not path.is_relative_to(root):
                raise ValueError("Inventory path escapes site: " + relative)
            paths.append(path)
        if len(set(paths)) != len(paths):
            raise ValueError("Duplicate inventory paths")
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as error:
        errors.append(f"Cannot load site inputs: {error}")
        return report
    documents = {}
    for path in paths:
        try:
            documents[path] = BeautifulSoup(
                path.read_text(encoding="utf-8"), "html.parser"
            )
        except (OSError, UnicodeError) as error:
            errors.append(f"Cannot read {path.relative_to(root)}: {error}")
    report["pages"] = len(documents)
    titles, descriptions, canonicals = [], [], []
    for path, doc in documents.items():
        issues, fields, title, description, canonical = validate_document(
            doc, path, root, config, documents
        )
        errors.extend(issues)
        report["answer_fields"] += fields
        titles.append(title)
        descriptions.append(description)
        canonicals.append(canonical)
    indexed = set()
    index = documents.get(root / "index.html")
    if index:
        for link in index.select("a[href]"):
            href = link.get("href")
            if not isinstance(href, str):
                errors.append("index.html: Link href must be a string")
                continue
            try:
                parsed = urlsplit(href)
            except ValueError:
                continue  # Already reported by validate_document.
            if not parsed.scheme and not parsed.netloc and parsed.path:
                indexed.add((root / unquote(parsed.path).lstrip("/")).resolve())
    for path in paths[1:]:
        if path not in indexed:
            errors.append("Not indexed: " + path.relative_to(root).as_posix())
    if inventory.get("issues"):
        errors.append("Unresolved inventory issues: " + str(inventory["issues"]))
    for label, values in (("titles", titles), ("descriptions", descriptions)):
        if len(set(values)) != len(values):
            errors.append("Duplicate SEO " + label)
    try:
        sitemap = ET.parse(root / "sitemap.xml")
        locations = {
            node.text
            for node in sitemap.findall(
                ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"
            )
        }
        if locations != set(canonicals):
            errors.append("Sitemap coverage differs from canonical URLs")
    except (OSError, ET.ParseError) as error:
        errors.append(f"Invalid sitemap: {error}")
    image_path = (root / config["social_image"]).resolve()
    if not image_path.is_relative_to(root):
        errors.append("Social image escapes site")
    else:
        try:
            data = image_path.read_bytes()
            if (
                len(data) < 24
                or data[:8] != PNG_SIGNATURE
                or struct.unpack(">II", data[16:24]) != (1200, 630)
            ):
                errors.append("Social image must be a 1200x630 PNG")
        except OSError as error:
            errors.append(f"Cannot read social image: {error}")
    for relative, phrase in (
        ("lectii/lectia-01-saluturi-si-expresii-uzuale.html", "hogy vagy?"),
        ("andras/lectia-01-cine-ce-face.html", "Ki beszél?"),
        ("comunicare/admiratie.html", "Ez aztán valami!"),
        ("gramatica/armonia-vocalica.html", "várok"),
    ):
        doc = documents.get(root / relative)
        if doc is not None and not any(
            phrase.lower() in node.get_text().lower()
            for node in doc.select("[lang=hu]")
        ):
            errors.append(relative + ": Hungarian example lacks language label")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Site directory")
    args = parser.parse_args(argv)
    report = validate_site(args.root)
    print(
        f"Validated {report['pages']} HTML pages and "
        f"{report['answer_fields']} exercise answers."
    )
    if report["errors"]:
        print("\n".join(report["errors"]))
        return 1
    print(
        "PASS: local links, fragments, assets, index coverage, structure, labels, "
        "answer keys, language samples, SEO metadata, sharing image and sitemap."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
