# Nebuló project instructions

This directory is a standalone static website. Run project commands from the
directory containing `index.html`, `biome.json`, and `tools/`, even when opened
inside a larger checkout. Keep changes within this project unless requested.

The HTML files are maintained sources. There is no framework build or dependency
on the original submission archives. Preserve Romanian document language,
Hungarian passage labels, source attribution, and Hungarian accented characters.

Use **Nebuló** as the public name, including headers, metadata, the PWA manifest,
and documentation. Skill identifiers use ASCII `nebulo-`. The existing `nebula/`
workspace path and legacy service-worker cache keys are technical identifiers;
do not rename them as part of a text or branding update.

Keep the 87 supplementary archives locally in `assets/original/leckek/fajlok/`.
Use `tools/restore_archives.py` for requested restoration and `audit_archives.py`
for integrity checks. Copy downloads as binary data; decoding and re-encoding
corrupts archives. Source URLs are derived in `audit_archives.py`; SHA-256 reports
can be regenerated during audits/restoration and need not be committed. Do not
extract legacy applications into the published site or add archives to the PWA
precache without a specific request.
Each archive download has a visible format and an adjacent Romanian
“Cum deschid arhiva?” link to `referinte/cum-deschizi-arhivele.html`.
Keep archive-specific starting filenames beside the download; put shared
extraction instructions in the guide instead of repeating them in lessons.

External HTTP(S) navigation links use `rel="noreferrer"`, a decorative ↗ marker,
and a Romanian screen-reader label. Preserve other `rel` tokens and the existing
tab behavior. Run `tools/mark_external_links.py` with the Python requirements for
a read-only audit; add `--write` after adding links, then format and rebuild offline
assets. Same-project links, fragments, email links and local downloads stay unmarked.

Typography uses self-hosted Literata (normal/italic WOFF2, SIL OFL in
`assets/fonts/literata/`). Keep both fonts in the service-worker shell and offline
inventory. Fluid font sizes use `progress(100vi, 400px, 1200px)` with rem outputs
and rem fallbacks in `site.css`; preserve the browser's default root font size.
Check small screens, 200% text sizing, missing-font fallbacks, and offline fonts
after typography changes. Do not restore mobile overrides that shrink lesson text.

## Local Codex skills

- [nebulo-biome-format](.agents/skills/nebulo-biome-format/SKILL.md): format or check
  HTML, CSS, JavaScript, and JSON with the project's pinned Biome version.
- [nebulo-python-tools](.agents/skills/nebulo-python-tools/SKILL.md): format Python
  with Ruff, run its linter and regression tests, and review the scripts in `tools/`.

Formatting commands and maintenance setup are also in [README.md](README.md).
Biome does not format Python, XML, SVG, or media in this configuration.
After HTML changes or generator output, run
`npx -y htmlhint@1.9.2 --config .htmlhintrc '**/*.html'` after Biome. Attribute
values use double quotes, including JSON attributes with internal `&#34;`.
Beautiful Soup generators use `serialize_html` from `tools/html_attributes.py`
to preserve this convention. See the Biome skill for repair and check commands.

The PWA's `offline-assets.js` is generated, not maintained by hand. After changes
to HTML, deployable assets, `sw.js`, README.md or LICENSE.txt, format the sources,
run `node tools/build-offline.mjs`, then format `offline-assets.js` with Biome.
Check with `node tools/build-offline.mjs --check` and
`node --test tools/test_pwa.mjs`. Preserve relative manifest/worker URLs so the
site works under a GitHub Pages project path. Cache neither external origins nor
the original RAR/ZIP downloads. Offline operation needs HTTPS or localhost.

For formatting-only requests, use formatter checks; run site validation when HTML
or site assets change. Do not run content-rewriting maintenance scripts merely
to format files. New tests are unnecessary for documentation-only changes.

For Python implementation changes, run the Python skill's ty type check, Ruff
lint check, formatter check, and offline regression suite. Formatting and linting
do not replace type checking. `ruff.toml` and `ty.toml` define the project's
rules and Python target. Keep imports free of
site reads/writes, and test content-rewriting tools on temporary sites.
