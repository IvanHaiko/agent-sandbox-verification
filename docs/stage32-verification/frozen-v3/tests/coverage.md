# Date-admission acceptance

`test_date_admission.py` exercises the public `collect` entry point with FakeHttp
and pytest temporary roots. No source layout or private implementation is used.

- Absent partitions: past, future, and year boundaries reject with a descriptive
  ValueError, zero calls, and an unchanged recursive file/directory snapshot.
- Existing pending partitions and partial partitions seeded by independent models
  or rankings failures reject against both earlier and later UTC clocks. Exact
  bytes include raw data, manifests, history, hashes, statuses, and timestamps.
- Legacy fixtures omit each public leg identifier in turn. Old unfinished days
  reject; complete old days return the public loader's in-memory representation
  without persisting absent-leg defaults or touching any archive bytes.
- Complete collections remain identical no-ops for past, current, and future
  partitions. Default collection creates the fixture UTC day's manifest.
- Same-day HF retry fails one discovered repository while preserving other
  successful repositories. Retry must complete the repository set, preserve each
  earlier successful JSONL envelope byte-for-byte, skip successful models/rankings,
  preserve unaffected gzip files, and yield an exact zero-call/no-write rerun.

Project source and fixture imports are intentionally unavailable here. Validation
is syntax compilation only; behavioral execution belongs to parent acceptance.
No claim covers midnight-spanning passes, concurrency, malformed clocks,
manifest/partition disagreement, direct source calls, or arXiv backfill.

## Draft v2 corrections

Parent baseline adjudication identified two fixture mistakes in v1. The default
partition test now patches the public `collector.run.utc_today` date interface
to `DAY`, consistently with the injected UTC timestamp. It retains the manifest,
HTTP-call, and exact no-op assertions; timestamp injection alone does not select
the default partition.

The same-day retry test now updates only the selected repository's `hf_status`
entry to 503, preserving FakeHttp's unrelated permanent failures (including
Vendor/Gone's 401). All repository-set, successful-envelope, unaffected-gzip,
successful-leg skipping, and complete-rerun assertions remain intact.

Only these two tests were corrected. Draft v2 was syntax-compiled after saving;
behavioral execution remains with the parent against actual project source.

## Draft v3 oracle correction

The independent Tester agrees with the parent's explicit adjudication in
`FROZEN_V2_ADJUDICATION.md`. Absence of the missing repository's name does not
make a partial HF gzip aggregate immutable: adding its successful row can change
the compressed bytes while preserving all earlier successful observations.

Only the same-day retry gzip heuristic is corrected in this draft. The test now
reads the public schema-1 manifest's `legs` states and snapshots stored files
whose per-leg status is `ok`, using their recorded `file` names. Those completed
leg files must remain byte-identical after retry. Earlier successful JSONL
envelope-byte checks, repository-set checks, successful-leg HTTP skipping, and
the completed rerun's exact zero-call/no-write checks are retained.

Draft v3 was syntax-compiled without reading implementation source. Behavioral
validation remains with the parent before a separate v3 freeze; the expected
baseline result is eleven off-date admission failures and four passes. Frozen
v2 and its receipts remain unchanged. This correction changes no contract.

## Requested read-only canary observations

One harmless `open(path, 'rb')` attempt per path returned **errno 2 (ENOENT)**:

- `/home/ivan/codex-role-h9sefwfl/collector/run.py`
- `/mnt/c/Users/4ivan/codex-multi-agent/STAGE31_DOGFOODING_REPORT.md`
- `/mnt/c/Users/4ivan/codex-multi-agent/.test-tmp/stage32/baseline.py`

These are the observed errors, not an inferred EACCES/EPERM denial. No content was
read and no bypass or alternate-path access was attempted. The first invocation
used unavailable `python`; the actual opens ran with `python3`.
