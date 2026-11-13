---
name: change-verification
description: Choose and run checks for code or tooling changes in the codex-agent-system support workspace.
---

Read `docs/guides/workflow.md` and `docs/guides/execution.md`. Select proportional
checks from actual changed behavior. New deterministic tooling needs focused
regressions for its failure modes; trivial reversible edits need no mirrored tests.
For support-module changes run the existing support suite. For documentation
tooling run its focused tests and `python scripts/docs.py check`.

Use existing project commands. Strict Linux isolation requires actual native
probes; Windows unit results cannot substitute for them. Preserve failures and
report real exits, skips and unresolved environment errors. Do not rerun successful
unrelated checks or create a new orchestration framework.
