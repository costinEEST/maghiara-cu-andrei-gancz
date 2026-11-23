---
name: nebulo-biome-format
description: Format or check Nebuló HTML, CSS, JavaScript, and JSON with pinned Biome. Use after HTML generators too. Do not use for Python, SVG, XML, or media.
---

# Format the static site with Biome

## Purpose

Format the requested sources without changing lesson text or behavior. Run from
the project root containing `biome.json`.

## Prerequisites

Use Node.js and npm/npx with the pinned Biome version below; no local npm install
or package.json is required. First use may need network access.

## Format the requested scope

For a bounded request, replace `.` in both commands below with the requested
file paths. Use `.` only when whole-project formatting is requested.

Format supported files:

```sh
npx -y @biomejs/biome@2.6.8 format --write .
```

Verify without modifying files:

```sh
npx -y @biomejs/biome@2.6.8 format .
```

Inspect any nonzero formatter result; do not suppress diagnostics to report a pass.

## Check HTML attribute quoting

Biome formatting does not enforce HTMLHint's attribute quote rule. After editing
HTML or running a generator, run this separate check **after** formatting:

```sh
npx -y htmlhint@1.9.2 --config .htmlhintrc '**/*.html'
```

Keep the glob quoted so HTMLHint checks nested pages on every shell. The checked-in
`.htmlhintrc` enables `attr-value-double-quotes` and is also discovered by the
HTMLHint editor extension. This focused check is not a full HTML/accessibility audit.
Single quotes are valid HTML, but this project uses double quotes consistently.
JSON attributes must escape their internal quotes, for example
`data-answers="[&#34;Reggel&#34;]"`; browsers decode that to valid JSON before
JavaScript reads `dataset.answers`. Do not replace JSON's double quotes with
apostrophes or double-escape existing entities.
Use numeric `&#34;` specifically: pinned Biome 2.6.8 rewrites named `&quot;`
entities as literal quotes and can switch the attribute back to single quotes.
The numeric reference survives formatting and satisfies HTMLHint too.

For existing single-quoted attributes, the DOM-preserving repair is:

```sh
uv run --no-project --with-requirements tools/requirements.txt python -B tools/html_attributes.py --write
```

Default invocation (or `--check`) is read-only and reports single-quoted attributes
and formatter-unstable named quote entities. HTMLHint additionally catches unquoted
or malformed values. Reformat repaired
files, rerun HTMLHint and site validation, then rebuild the offline inventory.
Python HTML generators use `serialize_html` from `tools/html_attributes.py`:
Beautiful Soup's default serializer can reintroduce single quotes around JSON.

## Limitations and project constraints

- `biome.json` enables experimental full HTML formatting explicitly, uses two
  spaces and a 100-column width, sets HTML `whitespaceSensitivity` to `css`, and
  enables `bracketSameLine`.
- Do not restore the old Prettier `strict` whitespace setting: it produced
  dangling brackets and joined structural tags in this site's generated markup.
- Do not switch to `whitespaceSensitivity: ignore` just to improve appearance.
  Inline emphasis splits Hungarian words into stems and suffixes; inserting
  spaces can change the examples.
- Preserve existing `biome-ignore format` comments around affected dialogue
  regions. Biome 2.6.8 alternates those line breaks between runs. Remove a
  suppression only after a formatter upgrade demonstrably makes the affected
  region stable and preserves its content.
- This is a formatting workflow. The configuration disables linting and assist;
  do not add behavioral fixes as an incidental part of formatting.
- Python uses Ruff. XML/SVG have separate formatting; leave audio, images, and
  downloadable archives unchanged.
- A Biome formatter pass does not review Python implementations. For Python
  changes, use the sibling Python skill's `ty check`, `ruff check`, and
  regression-test commands in addition to `ruff format --check`.

## Verify and refresh offline assets

After writing, run the check command on the same scope. If it still proposes changes, inspect the
diff instead of repeatedly formatting the entire site until it happens to pass.
After formatting changed pages, JavaScript, CSS or other offline assets, regenerate
the PWA inventory and check it:

```sh
node tools/build-offline.mjs
npx -y @biomejs/biome@2.6.8 format --write offline-assets.js
node tools/build-offline.mjs --check
node --test tools/test_pwa.mjs
```

The inventory includes README.md and LICENSE.txt; regenerate it after editing
those files too. Format source files before generating the inventory so its
content hashes match the final deployed files.
For HTML edits beyond formatting, also run:

```sh
python3 tools/check_links.py
```

Use the validation setup in the
[Python tools skill](../nebulo-python-tools/SKILL.md) to run `tools/validate.py`
when checking page structure, exercise keys, language samples, or SEO. Maintenance
scripts that serialize HTML may require another Biome pass afterward.

## Troubleshooting

- Repeated formatter changes: inspect the diff and preserve the existing dialogue
  suppressions; do not loop whole-site formatting to hide instability.
- HTMLHint quote failures: inspect the affected attributes and use the explicit
  DOM-preserving repair above only within the requested repair scope.
- Stale offline inventory: finish source formatting first, regenerate the
  inventory, format that generated file, then rerun its check.
- Missing Node.js, network access, or validator dependencies: report the blocked
  command and cause; a formatter pass does not establish site correctness.

Report the changed scope, completed checks, and any unresolved failures.
