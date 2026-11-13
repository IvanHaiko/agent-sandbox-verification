---
name: docs-sync
description: Update current project documentation when behavior or workflow changes affect its accuracy.
---

Find the project root containing `scripts/docs.py`. Read `docs/README.md`, then run
`python scripts/docs.py for PATH [PATH ...]` for changed files. Read mapped guides
and compare their claims with the change. For unmapped files, decide whether an
existing guide needs a related_files entry; avoid manufacturing documentation.

Update relevant current guides; API changes go to `docs/guides/reference.md`, and
the root README only when its front-page claims change.
Follow `docs/guides/documentation.md` for metadata. Preserve historical reports,
receipts and frozen tests. Run build then check; include the documentation outcome
at handoff. A docs-only edit still needs index checking, not unrelated runtime runs.
