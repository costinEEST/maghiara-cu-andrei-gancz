# Maintenance scripts and side effects

Read only the entry relevant to the requested audit or repair. Commands run from
the project root. An audit finding alone does not authorize repairs or deletion.

- `inline_cloze.py`: read-only audit by default; `--write` normalizes unambiguous
  number/speaker gutters and side-by-side independent exercises into one-column
  sentence flow. Translation/comparison matrices, nested and image tables remain.
  It preflights unchanged lesson text, fragment IDs and answer keys across all
  pages before writing. Keep authored dropdown choices; inline text fields grow
  from the student's input, not expected-answer lengths. After rewriting, check
  Biome/HTMLHint, site validation and script idempotence; use MCP for sentence
  wrapping, keyboard focus, typing growth, feedback placement, grading/reset and
  retained comparison tables, then rebuild the offline package.
- `convert_choices.py`: read-only audit by default; `--write` converts standalone
  short single-choice selects to native fieldsets/radios after all pages preflight.
  Preserve matching/ordering tasks, cloze fields, multi-select controls and long
  lists. `data-answers` belongs on the group, not individual radios. Multiple
  accepted strings are alternatives for one selection, not a request for checkboxes.
  Keep option language labels, bilingual true/false wording and original prompts.
  After conversion, check keyboard exclusivity, unanswered/wrong/correct grading,
  focus, reset and mobile wrapping in MCP, plus the usual Python, HTML and offline checks.
- `repair_prompts.py --sources /path/to/originals`: read-only comparison against
  original exercise HTML named after each local exercise page. Supply the complete
  set outside the site; add `--write` only for intended repairs after reviewing
  the reported pages. It recovers question/response rows and trailing sentence
  fragments from legacy radio quizzes, preserving explicit question-to-control
  labels and Hungarian language markup. It checks option counts and correct
  choice positions against the original key; uncertain mappings stop all writes.
  Source-backed spelling corrections update the solution list too. HTML5 table
  recovery uses the pinned `html5lib` maintenance dependency because many originals
  omit closing tags; no original JavaScript is executed. Number-only labels in
  ordering and odd-word tasks can be legitimate when the overall instruction
  defines the task. Never invent a missing stimulus from the answer options.
  After repair, rerun the read-only comparison (expect no changes), the Python
  checks, Biome, HTMLHint, site/link validation and offline inventory tests. Check
  representative repaired pages with MCP before declaring the source audit done.
- `html_attributes.py`: defaults to a read-only audit of single-quoted HTML
  attributes and named quote entities that Biome rewrites; `--write` repairs
  them after verifying the decoded DOM is unchanged
  for every affected file. It edits start-tag values only, preserving lesson
  spacing, scripts, comments and decoded answer JSON. Use its `serialize_html`
  helper for Beautiful Soup output rather than `str(doc)` so generators keep
  double-quoted attributes with `&#34;` inside JSON. After formatting, run
  `npx -y htmlhint@1.9.2 --config .htmlhintrc '**/*.html'` to catch single-quoted,
  unquoted or malformed attribute values; Ruff, ty and Biome do not enforce this
  HTML rule. Follow the Biome skill's validation and offline inventory workflow.
- `index_catalog.py --check`: audits encoding, all activity-to-lesson associations,
  sequential catalog numbers, visible titles and numeric order without writing.
  `--write` repairs known encoding errors and rebuilds the catalog from direct
  `.lesson-content` links. Run it after editing these links or adding activities;
  review parent associations, especially shared activities and legacy title
  mismatches. It preserves URLs and retains corrected legacy titles in the
  inventory when they conflict with the linked lesson. Never infer associations
  from filenames or sort display labels lexicographically. After `--write`, run
  `prepare_seo.py`, Biome, `index_catalog.py --check`, site validation, local link
  checks and the offline inventory workflow. New ordering deliberately renumbers
  later activities; keep external links based on stable paths, not catalog IDs.
- `check_links.py`: recursively checks local HTML/CSS paths and fragments. Add
  `--external --json link-report.json` only when an online reference audit is
  requested or needed. HTTP 404/410 means broken; timeouts, blocks, and rate
  limits remain unverified. A default offline pass proves nothing about remote
  reference availability.
- `audit_archives.py`: checks local archives; `--check-remote` verifies downloaded
  payloads in automatically removed temporary directories. Requires `bsdtar`
  (libarchive) for RAR and uses Python's zipfile CRC checks for ZIP. Run
  `python3 -B tools/audit_archives.py --check-remote --report archive-audit-latest.json`
  for a read-only online audit. `--replace-broken` additionally rewrites links and
  removes only confirmed broken local copies after the official archive passes
  decompression in that same run; it requires `--check-remote` and `--report`.
  Missing tools, unsupported compression and network failures are inconclusive,
  never permission to delete a file. JSON reports are generated audit outputs,
  not runtime inputs; use ignored root-level report paths and remove them when
  no longer needed. Source mappings remain in the script. Archive links
  that point externally need a visible Romanian online-download note, even inside
  Hungarian passages. The current edition keeps all 87 archives locally. Useful exercises can
  later become accessible HTML after content/license review.
- `restore_archives.py`: explicitly downloads and verifies all archive sources,
  stores binary originals under `assets/original/leckek/fajlok/` and rewrites links
  to local copies. Run `python3 -B tools/restore_archives.py --report archive-restoration-latest.json`
  when restoring/updating those assets is requested. All downloads must verify
  before publication; never decode/re-encode binary files, and never automatically
  extract executable legacy pages into the public site. Keep the special ZIP
  source mapping: its original host differs from Nebuló.ro. Record hashes and
  verify local integrity afterward with `audit_archives.py`. RAR/ZIP are deliberately
  excluded from the PWA precache; downloading them into the repository does not
  add them to offline storage.
- `repair_answers.py`: recovers missing Hot Potatoes cloze keys from supplied
  original HTML, parses string literals without executing JavaScript, and writes
  static solution lists plus `data-answers` and shared check/reset controls.
  `--sources` points to original files outside the site, named after their local
  pages. Default is a dry run; `--write` applies only after every page preflights.
  Respect the source charset and Hungarian accents. Only repair malformed Unicode
  escapes when an existing option confirms the resulting word. Missing selectable
  options must be backed by the source key. Never guess answers or generate
  solution lists only after the user submits an exercise.
- `validate.py`: checks the inventory, HTML structure, labels, answer keys,
  language samples, SEO, sitemap, and sharing-image dimensions.
- `prepare_seo.py`: rewrites page metadata and the sitemap from `site-config.json`.
  Preflights all pages and duplicate metadata before writing. Run it for an
  intended SEO/configuration update, not to format Python.
- `label_languages.py`: rewrites HTML language labels using conservative corpus
  and alignment rules. Inspect its audit output and mixed passages; it does not
  certify every linguistic label.

