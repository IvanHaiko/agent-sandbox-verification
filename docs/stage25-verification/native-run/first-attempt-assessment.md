# Stage 25 — Real-World Coding Challenge: Steam ETL

**Outcome: FAIL.** The framework did not complete Atomic Twitch Hour Replacement.
The Architect executed successfully against the actual pinned repository, but a
database access prerequisite failed inside the native sandbox. Execution stopped
before Implementer, Independent Tester, Controller acceptance and Reviewer.
There is no candidate patch and no Steam correctness verdict.

Recorded on 8 October 2026. Source repository: `C:\Users\4ivan\steam-etl`.
Fixed source commit: `0653617666399590c853c39f08e8cf97c9eca45c`.
The original checkout contained staged, unstaged and untracked work before the
experiment. Those changes were excluded from the fixed source copy and preserved.

## What executed

| Step | Result | Evidence |
|---|---|---|
| Framework README and Stage 24 inspection | Completed; native architecture preserved | Existing README and Stage 24 assessment |
| Fixed source extraction | Completed using `git archive`; project file hashes recorded | [Source manifest](docs/stage25-verification/native-run/source-manifest.json) |
| Architect | Completed in a fresh, private, read-only native repository | [Execution receipt](docs/stage25-verification/native-run/architect-execution.json), [proposal](docs/stage25-verification/native-run/architect-result.json) |
| Controller normalization | Completed; original task fields retained with explicit corrections/policies | [Canonical contract](docs/stage25-verification/native-run/normalized-contract.json), [normalization](docs/stage25-verification/native-run/contract-normalization.json) |
| Disposable PostgreSQL setup | PostgreSQL 18.6 started with Unix socket only; direct read-only diagnostic succeeded | [Diagnostic](docs/stage25-verification/native-run/runtime-controller-diagnostic.json), [server log](docs/stage25-verification/native-run/postgres.log) |
| Native sandbox database prerequisite | Failed in all four tested profiles | Probe receipts below |
| Implementer | Not started | No implementation artifact |
| Independent Tester | Not started | No independent design or test freeze |
| Controller acceptance | Not executed | No acceptance result |
| Reviewer | Not started | No review findings; this does not establish defect freedom |
| Framework regression suite | 37 passed, 0 failed, 0 errors, 0 skipped in WSL | [Final JUnit](docs/stage25-verification/framework-final-wsl.xml) |
| Cleanup and source integrity | Passed | [Controller assessment](docs/stage25-verification/native-run/assessment.json), [runtime cleanup](docs/stage25-verification/native-run/runtime-cleanup.json) |

The Architect used native Codex CLI **0.160.1**, **gpt-6.1-sol / medium**, with
`--no-daemon`, `--ephemeral`, `--ignore-user-config`, no inherited conversation,
disabled subagents and web search, and the existing restricted permission profile.
Native session: `01a11aba-4ef6-7341-bb0a-4edc8e9f00a8`. Its permission preflight,
unchanged full-workspace snapshot and owned process-group shutdown all passed.
Only one model role/context ran. Separation among multiple live role contexts was
therefore not exercised in this experiment.

## The blocker

Initially no PostgreSQL server or psycopg driver was available in WSL. The user
started Docker Desktop. Windows Docker was available and had PostgreSQL images,
but Docker integration was disabled for the Ubuntu WSL distribution. No Docker
execution backend was introduced and no existing container or production database
was changed.

The Controller downloaded and extracted PostgreSQL packages into a disposable
workspace runtime, installed the pinned target Python dependencies in a temporary
virtual environment, and started a private PostgreSQL cluster under an owned
`codex-role-*` directory. No system package installation or production credentials
were used. PostgreSQL listened only on its private Unix socket, with TCP disabled.

The native sandbox tests failed as follows:

| Native profile tested | Observed result |
|---|---|
| Existing `network.enabled=false`, plus bounded runtime/socket read grants | PostgreSQL connection: `Operation not permitted` — [receipt](docs/stage25-verification/native-run/runtime-probe.json) |
| Same profile plus the exact PostgreSQL `network.unix_sockets` allow entry | Same connection error — [receipt](docs/stage25-verification/native-run/runtime-probe-scoped.json) |
| Native proxy enabled, exact socket allowed, wildcard deny for domains | Configuration rejected: wildcard `*` is invalid in `network.denied_domains` — [receipt](docs/stage25-verification/native-run/runtime-probe-proxy.json) |
| Native proxy enabled, `mode=limited`, empty domain rules, exact socket allowed | PostgreSQL connection failed with `no error details available` — [receipt](docs/stage25-verification/native-run/runtime-probe-limited.json) |

The [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
documents native Unix socket allowlists and network proxy settings. The installed
CLI did not demonstrate a working contained database connection with the profiles
tested here. This is an observed compatibility/capability gap, **not proof that
every possible supported native configuration is incapable of PostgreSQL access**.
The precise underlying cause remains unresolved. The final profile's negative TCP
check was never reached because its database connection failed; no successful
proxy-containment claim is made.

A Controller read-only `SELECT current_database(), version()` against the same
socket succeeded outside the sandbox. This distinguishes a healthy database from
the failed sandbox access. It was prerequisite diagnosis only: no candidate or
acceptance test was executed outside isolation.

The challenge explicitly required stopping for a fundamental execution blocker
and prohibited silently weakening isolation. We stopped at this prerequisite
boundary. No broad-network or unsandboxed acceptance fallback, alternate model
route, additional agent, automatic model retry, or implementation by the Controller
was substituted.

## Engineering findings from the Architect

These are inspected facts and an approved proposal, **not implemented behavior**:

- `load_twitch_file(file_path: str | Path) -> int` returns an aggregate count. The
  Controller's initial interface summary incorrectly said `-> None`; normalization
  explicitly corrects that summary and preserves the actual interface.
- `fetched_at` is written as an aware UTC ISO string after the extractor's configured
  pagination loop. The parser yields naive UTC; legacy naive timestamps remain
  compatible. Database `sample_time` and `sample_hour` are timestamps without a
  timezone. `sample_hour` is the UTC hour floor; `snapshot_time` is insertion time.
- A conservative minimal proposal uses one transaction, serialization before the
  ordering read, upserts for retained games, and deletion of absent games. Retained
  row identifiers and insertion timestamps can thereby survive replacement. A table
  lock would serialize different-hour writers as a performance tradeoff.
- Proposed ordering: newer bronze observation wins; older input returns zero
  without mutation; an identical equal-time observation is a replay; conflicting
  equal-time contents raise `ValueError`. Historical `load_clock` rows do not establish
  true observation order. Missing times on existing bronze rows require explicit
  handling rather than an assumption that they are older.
- Actual Twitch bronze is a flat sample envelope. It has no durable pagination
  completion proof or per-hour watermark. Rejecting zero-aggregate observations
  avoids interpreting incomplete responses as authoritative empty input and avoids
  stale resurrection after an empty clear. Nonempty legacy compatibility cannot
  prove detection of unmarked upstream truncation. Supporting authoritative empty
  replacement would require a separate durable-watermark decision.
- Existing SQL-only unit mocks need necessary updates for lock/read/delete
  operations. `tests/test_load.py` was explicitly added to the Controller's proposed
  authorized scope for that purpose; no target file was actually edited.

## Capabilities established and not established

**Framework execution:** actual repository inspection by a native semantic role,
fixed-commit extraction, read-only isolation, structured result validation,
Controller normalization, artifact hashes, native identity, process shutdown and
cleanup worked. The complete engineering chain did not run. The label-normalization
fixture's existing offline tests remain functional; no additional live label run
was requested to mask this failure.

**Functional correctness:** untested. There is no implementation and no real
database acceptance of Twitch replacement, rollback, ordering, invalid-input
handling or concurrent loads.

**Code quality:** unassessed for the target change. Useful Architect findings were
produced, but no Implementer patch or independent Reviewer judgment exists.

**Test independence:** unexercised. No Tester received candidate data, because no
Tester ran. That fact is not evidence of successful blind design, freeze ordering
or independently designed acceptance.

**Remaining limitations:** real-repository writable execution and PostgreSQL
acceptance under the current native isolation remain undemonstrated. Empty-observation
semantics and upstream completeness evidence are additional bounded task limitations
identified during inspection. This stage does not claim arbitrary repository support.

## Changes, interventions and cleanup

The active addition is [validation/steam_workflow.py](validation/steam_workflow.py),
a small **preparation-only** driver accepting a local repository, full commit and
JSON task contract. It reuses the existing runner, owned workspace lifecycle,
snapshots, hashing and structured-output validation. It is not a completed
implementation/Tester/acceptance workflow.

The attempted writable-repository and database permission extensions were removed
from active code after the blocker. The original native runner was restored with
its exact Stage 24 SHA-256, `f62e57bf80765c78813aa988a09a9eecd91cfdb36f67684b4c3ca4e372b30a09`.
The Controller/roles/artifact architecture and label contract were preserved.
The [archived prerequisite source](docs/stage25-verification/native-run/executed-prerequisite-source)
records the diagnostics. Its `unexecuted-workflow-draft.py` was a draft, never a
successful run; it is outside active package discovery.

Manual interventions included elevated WSL access, Controller contract normalization,
the user's Docker startup, temporary dependency/database provisioning, correction of
PowerShell variable expansion during package extraction, and correction of an empty
owned-workspace setup input. An initial Windows framework-test invocation encountered
sandbox temporary-directory permission failures (3 failed, 26 errors, 7 passed,
1 skipped); the supported WSL invocation passed 37/37 before and after rollback.
None of these actions edited Steam production code or substituted a model result.

The Architect took **113.574 seconds**. The measured interval from native preparation
start through final evidence audit was **1,340.477 seconds** (about 22 minutes),
including environment diagnosis, temporary setup and cleanup. This interval excludes
the initial README inspection. Reliable token totals and billing consumption are
unavailable: the original receipts did not retain them. No estimates are reported.

The Architect repository, probe repositories, failed setup repository and PostgreSQL
cluster were removed. No `codex-role-*` directory remained at final audit. The recorded
PostgreSQL postmaster PID was absent, and the extracted runtime/virtual environment
was removed. Native role/probe process groups confirmed shutdown. Git HEAD, staged
and working binary diffs, status, and hashes of tracked/nonignored untracked target
files matched before and after. Ignored target data and credentials were not copied
or rewritten. This is an explicit logical-source integrity check, not a claim that
every internal Git cache byte was measured.

## Deliverables

Available: Architect proposal and native receipt; original/canonical contracts and
normalization; source/integrity manifests; explicit failed sandbox probes; healthy
database diagnostic; framework test XML; cleanup receipts; Controller decision; and
this assessment. The [evidence manifest](docs/stage25-verification/native-run/evidence-manifest.json)
hashes the retained run artifacts.

Unavailable: implementation patch, new automated Steam tests/results, independent
Tester design/freeze/acceptance, and Reviewer findings. No empty placeholder patch
was produced, and patch application to the source commit was not tested because
there is no patch. These missing deliverables make **FAIL** the appropriate final
outcome under the challenge's stated definition.
