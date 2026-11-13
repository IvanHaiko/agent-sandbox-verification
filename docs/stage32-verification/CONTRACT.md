# Collection-pass date admission

The daily collector archives live OpenRouter and Hugging Face observations in
`data/raw/<snapshot_date>/`. `snapshot_date` means UTC collection date, not a
historical source-effective date. A past usage observation cannot be reconstructed
by asking a current endpoint. The arXiv retrospective command has a separate
backfill namespace and is outside this change.

Observed baseline risk: `collect` skips complete manifests, but resumes incomplete
ones without checking their date. OpenRouter/HF legs then fetch live data and write
it into the requested partition. Only the arXiv leg has its own date check.

Required public behavior:

1. `collector.run.collect(root, snapshot_date=None, http=None, now=utc_now)` remains
   the entry point. Explicit dates are canonical `YYYY-MM-DD`; `now()` supplies a
   UTC ISO timestamp, as the existing API promises. Default date remains today UTC.
2. An already complete manifest remains a no-op even when its partition is old:
   return complete, make zero HTTP calls, and leave every file byte-identical,
   including manifest, run history, timestamps, legacy absent legs and raw payloads.
3. For any pass that would perform work, take its start timestamp from `now`.
   If the requested partition differs from that timestamp's UTC date (past or
   future), raise a descriptive `ValueError` before any HTTP request or file write.
   This covers both an absent day and any unfinished pending/partial day, including
   manifests lacking newer legs. No files or directories may be created or removed
   by rejection; no run entries, timestamps, hashes or statuses may be rewritten.
4. Current-day initial collection and current-day retry retain existing behavior:
   skip successful legs, retry failed work, preserve earlier successful observations,
   and retain the complete-day zero-call/zero-write rerun guarantee.
5. No schema, identity, payload format, source-event time, observation timestamp or
   ingestion provenance changes. No historical migrations or cleanup operations.

This is a pass-admission guarantee. A pass spanning UTC midnight, concurrent
collectors, malformed clock values, manifest/partition disagreement, and invoking
individual source modules directly are outside this bounded task. Do not claim
those are solved. The clock's documented UTC contract remains unchanged.

Authorized engineering paths: `collector/run.py`, `README.md`,
`tests/test_collection_date.py` (new implementation-local regression tests).
No other changes, dependencies or workflow infrastructure. CLI continues to expose
the entry point's ValueError as a nonzero failure; a new CLI error mechanism is not
required. README must explain same-day retry and old incomplete-day refusal.

Tester interface inputs:
- `collector.manifest.empty(date)` returns a schema-1 pending manifest;
  `save(path, manifest)` writes it; `load_or_empty(path, date)` loads it, filling
  absent legs in memory. `LEGS`, `OK`, `PARTIAL`, `PENDING`, `COMPLETE`,
  `NOT_APPLICABLE` are public constants. Complete older manifests fill absent
  legs as not_applicable in memory, without writing them back on a no-op.
- `collector.paths.manifest_path(root, date)`, `leg_path(root, date, leg)`,
  `LEG_FILES` and `collector.storage.read_gzip`, `write_gzip`, `write_json`
  are existing public fixture-building interfaces.
- `tests.conftest.FakeHttp`, `MODELS_URL`, `RANKINGS_URL`, `HF_API` and `clock`
  are existing public fixtures. `FakeHttp` has `calls`, `call_count`,
  `fail_urls={url: status}`, `hf_status={repo: status}`. Default responses
  complete every leg when the fixture UTC clock and partition both equal
  2026-08-29. Successful HF rows are newline-delimited JSON envelopes with
  `hf_id`, `fetched_at`, `http_status`, `body`.

Independent tests must run with pytest against actual project source, use isolated
temporary fixtures only, and never access real archives, external networks or
private sibling workspaces. Acceptance file: `tests/test_date_admission.py`.
Coverage explanation: `tests/coverage.md`. Import `FakeHttp` from
`tests.conftest` if needed. Project source and fixture imports will be available
when the parent executes the frozen suite. Test design should not prescribe code
structure or read implementation source.
