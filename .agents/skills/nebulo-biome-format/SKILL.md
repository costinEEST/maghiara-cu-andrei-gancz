---
name: nebulo-biome-format
description: Format or check this Nebuló project's HTML, CSS, JavaScript, and JSON with Biome. Use for formatting requests and after generators rewrite HTML; use the Python skill for Python files.
---

# Format the static site with Biome

Run commands from the project root containing `biome.json`, not from a parent
checkout. Use the existing configuration and pinned version; no local npm
installation or package.json is required.

Format all supported files:

```sh
npx -y @biomejs/biome@2.6.8 format --write .
```

Verify without modifying files:

```sh
npx -y @biomejs/biome@2.6.8 format .
```

For a bounded edit, replace `.` with the changed file paths. A nonzero formatter
exit status needs inspection; do not suppress diagnostics to report a pass.
First-time npx execution may need network permission in a sandbox.

## Project-specific constraints

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

After writing, run the check command. If it still proposes changes, inspect the
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
For HTML changes, also run:

```sh
python3 tools/check_links.py
```

Use the validation setup in the
[Python tools skill](../nebulo-python-tools/SKILL.md) to run `tools/validate.py`
when checking page structure, exercise keys, language samples, or SEO. Maintenance
scripts that serialize HTML may require another Biome pass afterward.
