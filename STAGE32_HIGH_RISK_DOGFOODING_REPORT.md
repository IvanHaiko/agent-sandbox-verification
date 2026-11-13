# Stage 32 — High-risk real-world engineering

Executed 10 October 2026. **Final verdict: PARTIAL.** A real temporal-integrity
defect was fixed, independent acceptance and project regressions passed, and the
confined Reviewer accepted the repaired implementation. Exact preservation of the
original Git index could not be established: its raw hash changed during the task.
The source, historical archives and observable staging semantics still match.
This prevents a High-risk PASS; it is not hidden by the green tests.

## 1. Selected engineering problem

The actual project is **Open Model Lifecycle**, at
`C:\Users\4ivan\ai-adoption`, original HEAD
`5121dd47adb2b69b2f64cca66609ebf8bd161868`.
Discovery examined daily collection/storage/manifests, HF individual and paginated
ingestion, arXiv daily/backfill paths, Silver deduplication/data-quality checks,
temporal archive indexing and provider identity history, persistence contracts,
public fixtures and existing tests. The project already distinguishes capture
time, source timestamps and materialization time, preserves explicit provider
identities, and has conservative replay/identity protections. No new identity or
temporal abstraction was needed.

`collector.run.collect` skipped complete days, but resumed unfinished days without
checking the collection date. Only arXiv had a date guard. A disposable baseline
reproduction first failed `Vendor/Beta` on August 29, then retried on August 30.
The retry fetched Beta, marked the August 29 snapshot complete, and saved its
August 30 `fetched_at` beside Alpha's August 29 observation. This can silently
distort daily usage analytics despite ordinary same-day idempotency tests passing.
See `docs/stage32-verification/baseline-reproduction.json`.

The public contract was fixed before implementation: completed partitions remain
exact no-ops; absent, pending and partial partitions may start work only when the
requested date matches the pass start's UTC date. Otherwise `collect` raises a
descriptive `ValueError` before any HTTP calls or writes. Same-day retries preserve
successful observations. Explicit arXiv backfill remains separate. Exact scope and
exclusions are in `docs/stage32-verification/CONTRACT.md`.

## 2. Implementation

The retained owned repository is
`C:\Users\4ivan\codex-multi-agent\.agent_worktrees\stage32-ai-model-lifecycle`,
branch `stage32/historical-collection-date`.

- Baseline commit: `7079fcfce5f2d14318f807104199db4d93b0a5f4`.
- Engineering commit: `c2358aaaf2c53bd2326562047f89ab2f6c1c4892`.
- `collector/run.py`: ten inserted lines admit unfinished passes using the existing
  start timestamp, after the completed-manifest early return. Parsing normalizes
  `Z` to `+00:00` for Python 3.10; recorded timestamp strings are unchanged.
- `tests/test_collection_date.py`: nine local cases cover absent/pending/partial
  rejection, legacy completed no-ops, successful-file preservation, and initial
  collection/retry with both UTC timestamp forms.
- `README.md`: replaces a misleading historical collection example and documents
  same-day retry, old incomplete-day refusal and the midnight limitation.

No dependencies, schemas, source payloads, provider/entity mappings, historical
timestamps, persisted observations, other pipelines or framework modules changed.
The deliberate compatibility change is refusal to populate an unfinished
off-date partition with live data. Completed historical partitions still return
without consulting the clock or writing absent-leg defaults.

`engineering.patch` and a verified, source-only Git bundle are retained in
`docs/stage32-verification/`. Every committed source byte matches the tested
candidate; the owned repository is clean. Nothing was pushed or merged.

## 3. Independent Tester and freezing

All worker roles used separate native CLI executions through the unchanged
Stage 30 `agent_system.execution` support, WSL Ubuntu and Codex CLI **0.160.1**.
Ordinary shared desktop agents were not substituted for enforced confinement.

The Tester received only the public contract and documented interfaces/fixtures.
It had no implementation, candidate, proposed diff, private handoff, repository
history or access to other workspaces. Its writable subtree was `tests/`; network
access was disabled. Both sandbox preflight and actual Tester tools denied reads
of existing harmless baseline-source and parent-evidence canaries with errno 2.
The parent checked the canaries' bytes remained unchanged. Evidence:
`tester-denials.json`, native execution traces and frozen coverage notes.

The first draft exposed fixture errors during admission. Its original bytes,
hashes and actual **13-failure/2-pass** baseline execution were preserved. Explicit
parent adjudication corrected default-date control and preservation of an unrelated
permanent HTTP failure through a targeted, still-blind Tester invocation.

Frozen v2 then exposed an additional incorrect oracle: it expected a partial HF
aggregate gzip to remain unchanged when the retry must append its missing row.
Its original bytes, receipt and **12-failure/3-pass** result remain intact.
Implementation stayed stopped. `FROZEN_V2_ADJUDICATION.md` records the parent's
decision; the independent Tester expressly agreed and changed the check to use
successful manifest legs, retaining exact prior-envelope preservation. There was
no unresolved oracle dispute and no production change to satisfy a bad expectation.

The corrected draft was run **before** the new freeze: **11 admission failures,
4 compatibility passes**, zero collection errors. Authoritative **frozen v3** was
created at **12:25:01 Europe/Berlin**; Implementer launch followed at **12:26:20**.
Original test bytes were copied unchanged into the fresh version. SHA-256 of
`tests/test_date_admission.py`:
`41daeca67ab3008a42ecf1e166d30574905ae27137361c81d51e98cc9e3bdc1a`.
The complete contract/test/coverage hashes are in `freeze-v3.json`.

Implementer preflight denied both reading and write-opening authoritative tests
and write-opening their receipt, errno 2. Frozen v2 and v3 remain hash-identical to
their receipts. The final suite covers past/future/year boundaries, absent/pending/
partial days, legacy absent legs, completed exact no-ops, same-day HF retry with
unchanged successful envelopes/files, and default UTC-date behavior.

## 4. Acceptance and historical integrity

Project-declared requirements were installed in a disposable environment:
Python **3.14.4**, requests **2.32.3**, pytest **8.3.3**, PyArrow **25.0.1**,
Ruff **0.6.9**. No original environment or credentials were loaded.

All checks ran through the existing Linux sandbox with source, frozen inputs,
historical fixtures and dependency runtime read-only. Only `.scratch/` was writable;
pytest temporary files were directed there and network access was disabled.
Actual commands, expanded in the JSON receipts, were:

```bash
# cwd: /home/ivan/codex-role-vkfd93to
# PY=/home/ivan/codex-role-d84s0i0h/venv/bin/python
# FROZEN=/mnt/c/Users/4ivan/codex-multi-agent/docs/stage32-verification/frozen-v3
env TMPDIR="$PWD/.scratch" "$PY" -B -m pytest -p tests.conftest \
  -c pyproject.toml "$FROZEN/tests/test_date_admission.py" -q \
  -p no:cacheprovider --basetemp=.scratch/independent \
  --junitxml=.scratch/independent.xml
env TMPDIR="$PWD/.scratch" "$PY" -B -m pytest tests -q \
  -p no:cacheprovider --basetemp=.scratch/regressions \
  --junitxml=.scratch/regressions.xml
/home/ivan/codex-role-d84s0i0h/venv/bin/ruff check --no-cache .
```

| Actual execution | Outcome |
|---|---|
| Unchanged baseline project suite | 134 passed |
| Unchanged baseline full Ruff | Passed |
| Initial candidate frozen acceptance / project suite / Ruff | 15 passed / 142 passed / passed |
| Repaired final candidate frozen acceptance | **15 passed**, 0 failures/errors/skips |
| Repaired final complete project suite | **143 passed**, 0 failures/errors/skips |
| Repaired final full Ruff | **Passed** |

The complete suite includes its real historical-baseline/read-only-index regression,
using byte-exact copied archives and validation records, not a mocked success or
replacement fixture. All **326** copied historical/validation files and complete
verification input hashes were unchanged after execution. All **316** protected
historical files in the original checkout matched before/after. No snapshots,
provenance, historical records or archived payloads were rewritten or regenerated.
No database exists in this project's verification path; database checks were not
applicable. Python 3.10/CI Python 3.12 and live provider checks were not executed.

The final deterministic Stage 30 `accept` decision is in `final-acceptance.json`.
It checks complete final source scope/required files, frozen hashes, real process
and test outcomes, final review and closeout integrity. **It does not accept the
overall High-risk result**, because original-index preservation is unresolved.

## 5. Independent Reviewer

The read-only Reviewer received baseline/candidate source, complete diff, original
contract, frozen suites, actual acceptance/regression outputs, historical compatibility
requirements, limitations and all oracle failures/adjudications. It received no
credentials or live production data. Parent confinement probes denied candidate
and test-copy write-opens with errno 30, and authoritative external write-opens
with errno 2. Actual Reviewer tools also observed errno 30. Input/candidate hashes
were unchanged after both review executions.

The initial Reviewer found a substantive issue beyond style: direct
`datetime.fromisoformat` parsing rejected valid `Z` timestamps on supported
Python 3.10, which the Python 3.14 green tests did not expose. It blocked acceptance.
After targeted repair and full retesting, the Reviewer returned
`accepted: true`, `blockers: []`. It confirmed the correction preserves recorded
timestamps, retry behavior, historical immutability and the original contract.
It accepted the explicitly documented oracle supersession.

A line-ending note was withdrawn after byte-level examination: the parent's
initial display diff had normalized only one side. The corrected diff exactly
matches candidate/baseline bytes; README was not changed in repair. The Reviewer
honestly noted that archived fixture bytes were not in its workspace; their integrity
was supported by parent execution evidence, not independently recomputed there.
See `review-v1.json`, `review-final.json` and reviewer confinement/integrity receipts.

## 6. Repairs, failures and escalation

There were no injected engineering faults. The findings arose from actual work.

One pre-freeze fixture correction, one explicitly adjudicated frozen-oracle
correction, and one targeted implementation repair occurred. Counting the latter
two against the High-risk repair budget uses **two of two** cycles. Successful
unrelated work was not restarted; the design and authoritative v3 stayed unchanged
through implementation repair and final review. The rejected candidate is preserved
in one small `rejected-candidate-v1.zip`.

Parent execution friction included resolving Codex through the established login
PATH, handling ownership markers in exported inputs, setting pytest TMPDIR, and
excluding pytest scratch symlinks from protected-input traversal. The installed CLI
failed individual-file writable mounts; the failure is preserved. The supported
profile instead allowed a bounded disposable `project/` directory, while the final
gate enforced the exact three-file change list. Frozen/private paths stayed denied;
this directory scope was disclosed, not silently substituted.

At closeout, the original raw Git index hash differed. Source work stopped. No
index restoration, reset, cleanup or speculative repair was attempted. The cause
is **undetermined**; this report does not attribute it to another process or claim
the task preserved bytes it cannot establish.

## 7. Repository protection and rollback

The original checkout had substantial existing source and historical-manifest
changes. It was never used as a worker/test output directory. A source-only owned
repository captured its current source working state, including selected untracked
source, separately from original HEAD. No original worktree registration was added.
The baseline commit and verified bundle provide rollback/recovery for the engineering
repository without altering the original.

Before/after receipts match **407 tracked/untracked file hashes**, **316 historical
file hashes**, HEAD, branch, status, staged/working diff hashes and worktree registry.
The sole differing captured field is `index_sha256`. The initial index was hashed
but its raw bytes were not saved: this was a protection gap in parent preparation.
Its post-run bytes are preserved as `original-index-after.bin`; hashes and observable
staging equivalence are recorded in `original-integrity.json`. A raw-byte rollback
of the original index is therefore unavailable. No original-repository write command
was issued, but that fact cannot replace the failed byte comparison.

Credentials, private notes and ignored production outputs were excluded from role
bundles and test execution. Ignored derived-output bytes were not baseline-hashed;
their byte-for-byte preservation is not independently established. No production
storage was connected or reset. Disposable source, runtime and fixture workspaces
remain available for inspection; no database/service was started. Every actual
role/check process group ended. No large runtime or historical-data archive was
created for delivery.

## 8. Operational experience

The native parent selected the risk, contract, sequence, exact change scope,
adjudications and repair decisions. **Seven native role invocations** were used:
three related Tester turns, Implementer plus one repair, and Reviewer plus targeted
re-review. Stage 30 execution/freezing/acceptance support was reused unchanged.
There is no Controller, scheduler, adapter, workflow engine, benchmark, artificial
fault campaign or metric collection infrastructure. Temporary one-shot parent command
cells live under `.test-tmp/stage32`; they do not form an installed/general workflow.

Isolation, fixture admission, package preparation, preservation and evidence assembly
required substantial manual coordination relative to a ten-line production change.
The faulty independent oracles show that independence does not establish correctness
without admission/adjudication. The Reviewer's Python-version finding demonstrates
value beyond repeated green tests. The final index audit also prevented an unjustified
PASS. High-risk overhead produced useful scrutiny here, but was considerable and
exposed a parent baseline-preservation weakness. No native-versus-custom comparison
or efficiency score is claimed.

## 9. Limitations

- The guarantee is admission of a collection **pass**. Crossing UTC midnight during
  a pass, concurrency and direct source-module calls remain outside scope.
- The existing UTC-clock contract is assumed; malformed/non-UTC clocks and
  manifest/partition disagreement are not solved.
- Python 3.10 compatibility was reviewed from source after repair, not executed;
  actual executable checks used Python 3.14.4, not CI's Python 3.12.
- No live API, production deployment, retrospective backfill or historical rewrite
  was executed. The real archive regression used a byte-exact isolated copy.
- Original-index raw-byte preservation failed, its cause is unknown, and its
  initial bytes are unavailable. Matching staging semantics is a narrower result.
- Reviewer archive-integrity assessment relied on recorded parent checks, and
  ignored production-output bytes were not independently audited.

## 10. Final verdict

**PARTIAL.** The selected engineering improvement is implemented, independently
tested first, frozen, verified against all existing regressions, repaired for a
real review finding and accepted by the confined read-only Reviewer. Historical
payload and captured source hashes are preserved; exact scope and frozen artifact
checks pass. The original raw-index mismatch blocks the required repository
protection guarantee, so the authoritative final acceptance remains rejected.

The engineering commit, patch, source-only bundle and minimal substantive evidence
are retained for inspection. A full High-risk PASS requires resolving the original
index-preservation issue; this run cannot manufacture the missing initial bytes.
