# Stage 31 — Real-world dogfooding

**Outcome: PASS.** Executed 10 October 2026, using the Stage 30 **Medium** profile.
The engineering task is complete, all 182 project tests passed without skips,
Ruff passed, independent native review accepted it, and final scope/integrity
checks passed. No orchestration infrastructure changed.

## Selected task and implementation

The current Steam migration runner used `sql.split(';')`. That breaks valid SQL
containing semicolons in literals, comments, or dollar-quoted procedural blocks.
Fixing the runner has direct database-maintenance value and needs no SQL parser,
dependency, migration rewrite, or production execution.

The Implementer replaced splitting with one parameter-free `cursor.execute(sql)`
per nonblank file. PostgreSQL handles SQL parsing. Existing filename ordering,
recorded-file skipping, and per-file commits remain intact. Blank files remain
recorded no-ops. Connection context handling rolls back a failed file.

Exactly three engineering files changed:

- `src/migrations.py`: whole-file execution and corrected docstring.
- `tests/test_migrations.py`: two unit regressions for intact SQL and blank files.
- `tests/test_migrations_db.py`: two real PostgreSQL regressions covering literal,
  comment and DO-block semicolons; blank/comment-only files; replay; DDL/DML and
  filename rollback; prior-file persistence; corrected retry.

## Repository protection and delivery

The original `C:/Users/4ivan/steam-etl` was dirty on `main`, at
`0653617666399590c853c39f08e8cf97c9eca45c`. Its 98 tracked/nonignored source files,
including pre-existing edits and additions, were copied into a separate owned
repository. Credentials and ignored data were excluded.

- Working copy: `.agent_worktrees/stage31-steam` under this workspace.
- Development branch: `stage31/migration-sql`.
- Rollback baseline: `c507bf15048cea275d7aa58595bca5d592abe292`.
- Engineering commit: `68edb39dec6a1ea0cdc99b8ac0ef1a107a7d4f38`.

The baseline represents the current source snapshot, not an upstream-history
clone. Pre-existing changes are in that baseline, separate from the engineering
commit. Nothing was merged or pushed. `baseline.zip`, `engineering.patch`, and a
verified `stage31-steam.bundle` are retained in `docs/stage31-verification/`.

Before/after receipts match for original file bytes, HEAD, branch, status, staged
and working diffs, raw index, and worktree registry. Ignored files were not read
or altered.

## Observed verification

The parent ran the unchanged `project_tooling/steam/verify.py` against the
engineering commit. It exported source, installed the project's pinned
requirements, and ran ordinary project commands in WSL using Python **3.14.4**
and disposable PostgreSQL **18.6** with an owned UNIX socket.

- Full `pytest tests` run: **182 passed, 0 failures, 0 errors, 0 skips**.
- JUnit contains **51 cases in database test modules**, including both new
  migration database tests and existing schema/query/loader checks.
- `ruff check --no-cache src tests`: **all checks passed**.
- `REQUIRE_DB_TESTS=1` prevented silent database skips.
- Verification source stayed unchanged; the TCP-denial check passed.
- PostgreSQL stopped, its PID disappeared, and owned test workspaces were removed.

The existing `accept` gate returned `accepted: true` with no failures. It compared
the complete source tree, including hidden/ignored entries, against the preserved
baseline; only the owned `.git` metadata was excluded from source inputs. The
changed set was exactly the three allowed paths. Changed file bytes also matched
the tested commit export. Actual execution receipts, native completion records,
review, original integrity, and service cleanup support the result.

## Workflow, failures, and friction

The native parent selected the task and exact scope, preserved the baseline,
delegated to a native Implementer, ran project verification, and applied the final
gate. A separate native Reviewer inspected code, fixtures, and actual results;
it accepted with no blockers. Agents shared filesystem access: this was independent
review, **not independently isolated or enforced read-only execution**.

One initial scoped Ruff run found I001 import ordering in the new test file.
The Implementer made one local correction and reran only that scoped check.
The full integration run passed first time; no integration repair or unrelated
agent/test repetition was needed. The original lint diagnostic is preserved.

Initial restricted-shell Git/WSL discovery was denied. Approved escalation allowed
read-only original Git inspection and disposable WSL execution. No auto-review
rejection or user clarification was needed. Diagnostics are retained.
A parent evidence-writing call also hit a JavaScript quoting error before
execution; correcting it required no engineering changes or repeated tests.

The support modules were straightforward to use. Source-only acceptance inputs
required excluding Git metadata explicitly, and the recipe requires Linux, native
Codex permissions, package provisioning, and explicit lifecycle handling. Those
were the main manual steps. The parent recorded native completion separately
instead of inventing subprocess exit codes for desktop agents. No Controller,
obsolete driver, new orchestration script, adapter, benchmark, or monitoring
subsystem was introduced; token usage was not measured.

## Limitations and final assessment

Verification used the established Stage 30 WSL environment, not CI's Python 3.10
runtime. Existing migrations and the complete current source snapshot passed;
production databases and APIs were not exercised. Concurrent migration locking
and explicit transaction-control statements inside authored SQL remain outside
this task. No unchanged-baseline suite run or mutation benchmark was performed.

Medium was proportional: one small production change, focused regression tests,
one reviewer justified by transaction behavior, and the project's existing full
checks. The final result establishes useful behavior and exact scope, while
making no stronger isolation claim. Native orchestration was sufficient and the
change remains small and maintainable.

Evidence: `docs/stage31-verification/acceptance.json`, `review.json`,
`original-integrity.json`, `test-summary.json`, `project-execution.json`, and
`project/{pytest.json,ruff.json,results.xml,result.json}`. Full source/runtime
archives and diagnostic outputs remain available there for review.
