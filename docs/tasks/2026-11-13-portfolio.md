# Portfolio repackaging — 13 November 2026

Result: the root README is now the project's front page, written for a reader who
spends a minute on it:
- what the problem is;
- a results table generated from the Stage 34 evidence;
- a Mermaid architecture diagram;
- three findings with their numbers and links to the stage reports;
- a demo with recorded output;
- day-to-day use, a repository map, a research log of Stages 24–34, and limits.

The detailed material moved into current guides without changing its meaning:
- the API, trust model, failure handling, examples and rollback went to
  `docs/guides/reference.md` (new);
- Git-index protection went to `docs/guides/acceptance.md`;
- the high-risk steps went to `docs/guides/workflow.md`.

Tooling: `scripts/docs.py build` now also renders the README results table from
`docs/stage34-verification/summary.json`. `check` fails when that table drifts from
the evidence, or when a relative link in the README, AGENTS.md, CLAUDE.md or a
current guide is broken. Three regression tests were added.

Publication size: `docs/stage31-verification/project/runtime-closeout.zip` (94 MB of
downloaded dependency bytes) is excluded by `.gitignore`. Its hash and reason are in
`docs/publication-exclusions.json`, following the Stage 30 precedent. The file stays
locally.

Privacy: at the user's request, four Stage 32 files are also excluded, all of them
kept locally and unmodified. They carry the target project's source with a personal
contact address in its User-Agent constant:
- `implementer-execution.json` and `reviewer-execution.json` (raw worker logs);
- `rejected-candidate-v1.zip`;
- `stage32-ai-model-lifecycle.bundle`.

Their hashes and reasons are in `docs/publication-exclusions.json`. The publishable set
was checked with `git add --dry-run` through a temporary git directory outside the
workspace: 2048 files, 43.1 MB, no excluded or ignored paths. It was then scanned,
including zip, gzip, tar and nested archives, plus the trees of both git bundles. No
email address or API token pattern remains.

Deliberately not moved: the root `STAGE*.md` reports and `stage29-delivery.zip`.
Evidence manifests, receipts and Stage 32 frozen tests record these paths, so moving
them would break the history's verifiability. The README presents them as a
research log instead.

Checks:
- every README claim was compared with the evidence, and three were corrected:
  - module size is now about 450 lines;
  - the `/mnt/c` gap is described as found in code review, not reproduced live;
  - the demo output is marked as condensed;
- the architecture diagram is a static SVG rendered from `docs/architecture.mmd`
  with Mermaid 10.9.1 (`scripts/render_diagram.py`), and `docs.py check` verifies
  its source hash. GitHub's inline Mermaid viewer had shown the first, wide version
  in a clipped 180 px frame; the published README was checked again after the change;
- `pytest`: 56 passed, 4 skipped (after the diagram check was added);
- `docs.py check`: OK.

Not done: a recorded GIF demo (no recording tool available), and renaming the
repository (the folder name and package name stay; the GitHub name is the user's choice).

Published on 13 November 2026 at https://github.com/IvanHaiko/agent-sandbox-verification
(public; commits authored with the GitHub noreply address).
