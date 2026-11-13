# Stage 25 — Real-World Coding Assessment: Steam ETL

**Final outcome: PASS.** The native workflow delivered a reviewable Atomic Twitch
Hour Replacement patch. Controller acceptance passed **234 tests**, including
**29 independently designed PostgreSQL tests**, with **zero failures, errors or
skips**. The read-only Reviewer recommended acceptance with no blockers or findings.
The original repository is unchanged, the patch applies to the fixed source commit,
and temporary repositories, database processes and runtime files were removed.

This result follows the user's explicit request to retry and test properly. The
[first attempt and its FAIL assessment](docs/stage25-verification/native-run/first-attempt-assessment.md)
remain preserved. Successful completion required manual environment diagnosis and
one acceptance startup continuation; this is evidence of useful engineering work,
not a claim that the experiment ran unattended.

## Scope and delivered change

Target: `C:\Users\4ivan\steam-etl`, fixed source commit
`0653617666399590c853c39f08e8cf97c9eca45c`. Work used isolated copies of that commit,
excluding the target checkout's unrelated staged, unstaged and untracked changes.

The [clean implementation patch](docs/stage25-verification/retry-1/steam-etl-implementation.patch)
changes exactly five project files: `src/load.py`, `src/transform.py`,
`tests/test_load.py`, new `tests/test_twitch_hour_replacement.py`, and new
`docs/TWITCH_HOUR_REPLACEMENT.md`. The new test module contains 37 collected cases.
No migration, historical bronze file, unrelated loader or downstream query changed.
The [candidate manifest](docs/stage25-verification/retry-1/candidate-manifest.json)
records the delivered bytes. Patch SHA-256:
`98faa8b05509d33576bd7872a37498b7e58510dca8e69373e4da4d4e896c1e8a`.

The loader validates an entire incoming observation before opening a database
connection. A single READ COMMITTED transaction takes a SHARE ROW EXCLUSIVE table
lock before reading the stored hour, checks observation ordering, upserts incoming
games, deletes absent games from that hour, and commits once. For the task's
A/B/C → A/C/D example, B disappears and the resulting hour contains exactly A/C/D.
Retained row IDs and insertion timestamps survive; other hours retain their contents.

`load_twitch_file(file_path: str | Path) -> int` preserves its existing public
interface: initial loads and identical replays return the aggregate count; stale
observations return zero with an explicit diagnostic. An identical equal-time logical
observation performs no persisted writes. Conflicting equal-time contents raise
`ValueError`. Older bronze observations cannot replace newer ones. Historical
`load_clock` rows do not establish a genuine bronze observation ordering; bronze
rows with missing observation times are rejected rather than silently ordered.

Full ISO datetime `fetched_at` is required; aware values are normalized to naive UTC,
legacy naive values are treated as UTC, and `sample_hour` is the UTC hour floor.
`sample_time` remains observation time, `sample_time_source` remains provenance, and
`snapshot_time` remains insertion time. The Controller corrected an initial `-> None`
interface summary explicitly in the [contract normalization](docs/stage25-verification/retry-1/contract-normalization.json).
Original task fields and criteria were retained in the [canonical contract](docs/stage25-verification/retry-1/normalized-contract.json).

Empty or zero-aggregate observations, malformed input and explicit failure/incomplete
envelopes are rejected without clearing stored data. Nonempty legacy envelopes remain
accepted. Optional source, request and stream-count fields are validated when supplied.
Legitimate blank unassigned categories retain their existing filtering behavior.
Authoritative empty clears would need durable ordering state; no speculative watermark
migration was introduced.

## Actual native workflow

Architect → Implementer → blind Independent Tester → deterministic Controller
acceptance → read-only Reviewer completed. All four roles used native Codex CLI
**0.160.1**, exact **gpt-6.1-sol / medium**, separate ephemeral contexts and private
repositories, without inherited conversation history. Native authentication remained
owned by Codex. There was no custom transport, Docker model backend, alternate model,
automatic model retry or additional agent.

| Role | Native session | Duration | Result |
|---|---|---:|---|
| Architect | `01a11aba-4ef6-7341-bb0a-4edc8e9f00a8` | 113.574 s | Successful read-only proposal, reused unchanged from the first attempt |
| Implementer | `01a11ade-366c-72b0-86b0-b96155740343` | 337.812 s | Candidate, tests and handoff collected; scope checks passed |
| Independent Tester | `01a11ae3-5fce-7941-9f66-d83e549da533` | 329.772 s | Blind design and executable harness frozen |
| Reviewer | `01a11aeb-92e7-7ee3-9591-f0b318ab9b77` | 34.776 s | Accept; zero blockers and findings |

The Implementer ran lint/AST checks and truthfully reported that its functional
pytest invocation could not start in the role environment. The Controller later ran
the entire candidate suite against real PostgreSQL. No Implementer or Tester output
was resampled to improve acceptance.

The Tester received only approved contract/public interface material, the unchanged
database fixture and test-design schema. It received no `src` tree, implementation,
diff, handoff or Architect approach. [Tester context](docs/stage25-verification/retry-1/tester-context.json)
and [native execution receipt](docs/stage25-verification/retry-1/independent_tester-execution.json)
record that boundary. Its workspace was removed before candidate exposure.
The [design](docs/stage25-verification/retry-1/frozen-test-design.json) and
[executable harness](docs/stage25-verification/retry-1/frozen-acceptance.py) were hashed
and [frozen](docs/stage25-verification/retry-1/test-freeze.json) before the separate
[candidate exposure](docs/stage25-verification/retry-1/candidate-exposure.json).
Acceptance and review did not modify candidate bytes.

## Functional test evidence

A disposable **PostgreSQL 18.6** cluster used the existing project migrations and
database fixtures. `REQUIRE_DB_TESTS=1` prevented unavailable-database skips. The
full suite includes unit and database tests; database correctness rests on actual
PostgreSQL execution, not SQL mocks alone.

| Verification | Passed | Failed | Errors | Skipped | Evidence |
|---|---:|---:|---:|---:|---|
| Complete candidate suite | 234 | 0 | 0 | 0 | [JUnit](docs/stage25-verification/retry-1/acceptance.xml), [stdout](docs/stage25-verification/retry-1/acceptance-stdout.txt), [receipt](docs/stage25-verification/retry-1/acceptance.json) |
| Independent acceptance subset | 29 | 0 | 0 | 0 | Included in the same JUnit; 10 designed scenarios covering all eight requested categories |
| Framework/label regression suite | 40 | 0 | 0 | 0 | [WSL JUnit](docs/stage25-verification/retry-1/framework-final-wsl.xml) |
| Frozen independent suite on unchanged source | 7 | 22 | 0 | 0 | [Negative-control JUnit](docs/stage25-verification/retry-1/baseline-control.xml), [receipt](docs/stage25-verification/retry-1/baseline-control.json) |

Candidate pytest reported 5.31 seconds; the negative control reported 5.50 seconds.
The 22 baseline failures are expected and demonstrate that the frozen suite detects
the original membership and concurrent-observation mixture defects. This was a
deterministic negative control, not another candidate or model attempt.

The independent tests verify initial aggregation and UTC/provenance semantics;
replay equality across every persisted column and PostgreSQL `xmin`; changed
membership with retained identities; untouched neighboring hours; stale and
equal-time ordering; legacy clock provenance; invalid/incomplete envelopes; and
concurrent loaders for both absent and existing hours.

Rollback uses an actual PostgreSQL trigger failing the second row write. A
nontransactional sequence confirms that earlier write progress occurred; every
column of the previous complete observation survives the failed transaction.
Concurrency uses two real worker sessions, a barrier and a table-lock gate;
`pg_stat_activity` confirms overlapping blocked sessions before release. Bounded
timeouts prevent indefinite hangs. Both schedules finish with exactly the newer
complete observation, and a subsequent stale replay cannot resurrect removed games.
These are meaningful finite schedules, not an exhaustive concurrency proof.

## Review and assessment boundaries

The [Reviewer result](docs/stage25-verification/retry-1/reviewer-result.json) recommends
`accept`, with empty `blockers` and `findings`. It inspected source, patch, contract,
handoff and frozen acceptance evidence read-only. It identified no concrete blocking
defect; it did not rerun tests or modify code. Its acceptance is a review judgment,
not proof that no undiscovered defect exists.

- **Framework execution:** the fixed-source, writable-role, blind-design, freeze,
  acceptance, review, patch and cleanup sequence completed. Original label behavior
  remains covered by the passing framework suite. The run required manual setup.
- **Functional correctness:** all material requirements passed the independent real
  database suite and full regression suite. The unchanged-source negative control
  demonstrates discrimination between the original implementation and the candidate.
- **Code quality:** the patch stays within five authorized files, reuses the existing
  row-upsert helper, preserves interfaces and schema, and documents ordering and input
  policies. Reviewer found no blocking correctness or maintainability issue.
- **Test independence:** separate context/input scope, frozen hashes and exposure
  ordering were verified. Test expectations preceded candidate access. Existing
  tests and Implementer tests provide additional regression coverage, not blindness.
- **Remaining limitations:** the table lock serializes writers across different
  hours; authoritative empty clears remain unsupported; unmarked upstream truncation
  cannot be detected from legacy envelopes. “Complete” means the configured Twitch
  stream sample, not every live stream. The per-row helper alone does not provide
  complete-observation ordering. This one repository experiment does not establish
  arbitrary-repository support or host-wide containment.

## Environment failures and explicit interventions

The first attempt stopped before implementation after contained PostgreSQL access
failed. Docker Desktop was started by the user, but Ubuntu's Docker integration was
disabled. The retry used a native disposable database, without changing existing
containers or production credentials. Packages were extracted into a workspace
runtime rather than installed as system packages.

Direct socket diagnostics isolated the blocker: the tested CLI restricted proxy
profiles did not permit the direct AF_UNIX socket creation needed by psycopg. An exact
proxy Unix-path allowlist did not make that kernel operation work. For deterministic
Controller database commands only, the native profile now permits Unix socket
syscalls and grants filesystem access to the owned PostgreSQL socket directory.
It executes inside a fresh user/network namespace via
`unshare --user --map-root-user --net`, then the native Codex filesystem sandbox.
The `dangerously_allow_all_unix_sockets=true` setting is a broader syscall capability;
the namespace and filesystem restrictions bound its use. It is not described as a
narrow capability on its own. Model-role commands retain network disabled and receive
no database grant.

The [IPC diagnostic](docs/stage25-verification/retry-1/socket-namespace-ipc.json)
confirmed access to the authorized pathname socket and failure to reach an unlisted
pathname, host abstract Unix socket or host TCP sentinel. The
[contained PostgreSQL probe](docs/stage25-verification/retry-1/runtime-probe-contained.json)
then succeeded. These specific observations support this bounded setup; they are
not a general sandbox security proof.

Two Python environment issues also required intervention: pinned dependencies had
to be localized into the temporary virtual environment, and pytest needed an
authorized `TMPDIR` rather than its denied default. The first Controller acceptance
process failed before collection; its `environment-failure-*` receipts are preserved.
The [explicit continuation](docs/stage25-verification/retry-1/acceptance-continuation.json)
verified unchanged candidate, patch, contract and frozen test hashes before rerunning
the outstanding acceptance and invoking the one outstanding Reviewer. No acceptance
ran unsandboxed, no target code was written by the Controller, and no role was retried.

Active extensions are the task-specific `validation/steam_workflow.py`, temporary
runtime/diagnostic helpers, and small native-runner additions for bounded multi-file
edits, runtime reads and Controller database commands. Existing artifact, workspace,
role/schema and native execution mechanisms were reused. Controller/roles/artifacts
architecture and the label contract were preserved; no generic task language or
backend plugin architecture was added. `steam_resume_acceptance.py` is an explicit
guarded startup-failure continuation, not an automatic retry mechanism.

Role execution totaled **815.934 seconds**, including the reused Architect. The
second workflow through review took **979.451 seconds**; its start through final
integrity audit took **1,365.767 seconds** (about 22 minutes 46 seconds), including
negative control and cleanup but excluding earlier prerequisite diagnosis. Native
reported counters are Implementer **69,054**, Tester **43,826**, Reviewer **47,430**:
partial total **160,310**. The Architect counter was not retained. These counters
are not complete billing consumption or dollar estimates.

## Integrity, cleanup and deliverables

The [final integrity audit](docs/stage25-verification/retry-1/final-integrity-audit.json)
verifies original HEAD/status, staged/working binary diffs, and hashes of tracked and
nonignored untracked files unchanged. Ignored target data and credentials were not
copied or rewritten. This is a logical-source comparison, not a comparison of every
internal Git cache byte. `git apply --check` and actual application in a separate
fixed-source workspace recreated the archived candidate. The candidate stayed
unchanged after tests and review.

All owned role repositories were removed, no `codex-role-*` directory remained,
the recorded PostgreSQL postmaster PID was absent, and the extracted runtime and
virtual environment were removed. Role process-group shutdown checks and
[runtime cleanup](docs/stage25-verification/retry-1/runtime-cleanup.json) passed.

All five requested deliverables are present: clean patch; automated project tests
and results; independently frozen design/harness and acceptance evidence; Reviewer
findings; and this assessment. A [portable delivery ZIP](docs/stage25-verification/retry-1/steam-etl-stage25-delivery.zip)
contains the patch, independent test module/design, test results, review, audit and
usage instructions. Full receipts remain in `docs/stage25-verification/retry-1` and
are hashed by its [evidence manifest](docs/stage25-verification/retry-1/evidence-manifest.json).
The [Controller decision](docs/stage25-verification/retry-1/controller-decision.json)
and [machine-readable assessment](docs/stage25-verification/retry-1/assessment.json)
record **PASS**, with the manual interventions and limitations retained.
