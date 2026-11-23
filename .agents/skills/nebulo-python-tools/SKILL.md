---
name: nebulo-python-tools
description: Review, type-check, lint, format, and test Nebuló Python maintenance tools. Use for Python changes or implementation reviews, not lesson prose or frontend formatting.
---

# Maintain Python tooling

## Purpose

Maintain `tools/` without corrupting Romanian instructions, Hungarian examples,
answer keys, or published assets. Run commands from the project root containing
`tools/`, `ruff.toml`, and `ty.toml`.

## Prerequisites

Use `uv` with the pinned versions below and `tools/requirements.txt` for Beautiful
Soup and HTML5 parsing dependencies. First use may need network access; the
regression suite itself runs offline. Python targets 3.10 in both tool configs.
If uv is unavailable, use the virtual-environment commands in
[references/environments.md](references/environments.md).

## Choose the workflow

- **Formatting only:** format the requested Python files, then run type, lint,
  and formatter checks. Do not run content-rewriting tools to format code.
- **Implementation changes or review:** run all four checks below. Add focused
  regressions for behavior changes, using temporary sites and mocked downloads.
- **Site audit or repair:** read the relevant entry in
  [references/maintenance-scripts.md](references/maintenance-scripts.md) before
  running that tool. Use its read-only mode unless repairs are requested.
- **Documentation only:** no Python regression run is needed.

For a bounded formatting request, replace `tools` with the requested paths:

```sh
uv tool run --from ruff==0.14.4 ruff format --no-cache tools
```

## Required checks

```sh
uv tool run --from ty==0.0.107 --with-requirements tools/requirements.txt ty check tools --error-on-warning
uv tool run --from ruff==0.14.4 ruff check --no-cache tools
uv tool run --from ruff==0.14.4 ruff format --no-cache --check tools
uv run --no-project --with-requirements tools/requirements.txt python -B -W error -m unittest discover -s tools -p 'test_*.py'
```

The last command is required for implementation changes and reviews. Formatting
alone does not verify types or behavior. Fix type mismatches rather than adding
blanket ignores or unverified casts. Beautiful Soup attributes can be strings or
lists; validate before JSON decoding. Guard DOM queries that return `None` with
useful errors. Overrides preserve base-class keyword names and accepted types.
Review lint fixes before applying them; `ruff check --fix` is not a formatter.

## Site validation

When changes affect HTML, exercise keys, language markup, metadata, inventory,
or validation rules, validate the actual site too:

```sh
uv run --no-project --with-requirements tools/requirements.txt python -B tools/validate.py
python3 tools/check_links.py
```

After a tool writes HTML, follow the
[Biome skill](../nebulo-biome-format/SKILL.md) for formatting, HTMLHint, and offline
inventory checks. Format the final sources before rebuilding their hashes.

## Limitations and side effects

Importing maintenance modules must never read or rewrite the site; CLI execution
belongs behind `if __name__ == "__main__"`. Preserve the import-safety regression.
Use `--root` where supported to exercise generators on temporary fixtures, never
maintained lessons merely as a smoke test. Text I/O uses explicit UTF-8.

Source-backed repairs need original files outside the published site. Do not
invent missing prompts or answers, execute legacy JavaScript, or decode binary
archives as text. A failed download or unsupported decompression is inconclusive,
not evidence that an archive should be deleted. Keep archives outside PWA caches.

## Troubleshooting

- Unresolved Beautiful Soup types: use the requirements-enabled ty command above
  or install the maintained requirements in the editor's selected environment.
- A regression tries to access the network or real lessons: isolate its files
  and mock the external operation before rerunning it.
- Missing originals, tools, or dependencies: report the unverified check and its
  cause; do not treat a skipped or failed check as a pass.

Report the changes, checks performed, and unresolved failures. Retain requested
reports and useful ignored environments; remove accidental task artifacts.
