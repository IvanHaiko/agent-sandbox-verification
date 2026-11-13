# Stage 30 — Native Codex migration

Executed **10 October 2026**. Stage 29's **SIMPLIFY** decision was implemented.

## A. Executive outcome

**Migration completed.** Native Codex now owns task interpretation, role selection,
conversations, sequencing, implementation and targeted repair. Ordinary small work
uses one native session. The old Controller is **deleted and inactive**.

The installed package contains two support modules and an initializer:

- `execution.py`: native CLI permission arguments, selected environment filtering,
  command construction and owned process-group lifetime.
- `acceptance.py`: explicit public inputs, private source workspaces, executable-test
  freezing, complete final scope/integrity checking and preservation before cleanup.

There is no replacement scheduler, workflow engine, task DSL, role hierarchy,
authentication implementation or compatibility API. One standalone clamp example
and one Steam-specific project verification recipe remain outside the package.

All four phases were completed in dependency order: replacements were demonstrated
before deleting the mechanisms they replace. A verified source-only rollback archive
was created before active changes. Original Steam source/index/worktree metadata and
680 historical Stage 25–29 evidence/report/archive files remain unchanged.

## B. Architecture before and after

Before:

```text
labels driver -> Controller -> artifact admission/freeze -> generated labels harness
             -> semantic role schemas/normalization/review
             -> NativeLinuxCodexRunner -> native CLI
Steam drivers -> their own role sequences/acceptance/review -> same runner
             -> RoleTestEnvironment mailbox -> contained pytest/Ruff
Steam runtime/control/probe drivers -> fixed experiment provisioning and checks
```

After:

```text
Native Codex parent
  -> ordinary native development session for small/medium work
  -> explicitly restricted CLI sessions for independent high-risk roles
  -> project commands for verification
  -> accept(observed facts) -> one final decision

execution.py  -> native permissions/exec/sandbox + owned process shutdown
acceptance.py -> source inputs/freeze/scope/preservation
project_tooling/steam/verify.py -> disposable exported project's pytest/Ruff/PostgreSQL
```

Custom role ordering, canonical task echoes, role-specific schemas, primary-target
admission, generated harness conventions, banner parsing, duplicated final decisions
and the mailbox request/response thread were eliminated. They were not renamed.

`accept` runs no commands and schedules no agents. The native parent passes every
required observed process/check outcome and actual review. It rejects missing or
unsuccessful outcomes, missing final artifacts, unauthorized additions/deletions/
modifications, frozen drift, blockers and unresolved environment failures. Its three
failure groups are process/environment, artifact/scope and behavior/review.

## C. Removed components

Deleted from active source:

- `agent_system/controller.py`
- `agent_system/roles.py`
- `agent_system/native_codex_linux.py`
- `agent_system/artifacts.py`
- `agent_system/test_environment.py`
- `validation/native_workflow.py`, `validation/labels_contract.py`
- `validation/steam_workflow.py`, `validation/steam_refactoring.py`
- `validation/steam_runtime.py`, `validation/steam_negative_control.py`
- `validation/steam_resume_acceptance.py`, `validation/steam_sandbox_probe.py`
- The unused `validation/__init__.py`
- The five tests devoted to those removed APIs: `test_controller.py`, `test_roles.py`,
  `test_native_launcher.py`, `test_acceptance.py`, `test_test_environment.py`.

`jsonschema` and the old normalization/design/review schemas are gone. Packaging is
version 2.0.0, with no runtime Python dependencies and pytest as a development extra.
No removed API has a shim. Import inspection confirms the surviving runtime,
example, project recipe and focused tests do not require the deleted modules.

The process-group helper remains deliberately: native managed cancellation has not
demonstrated the same shutdown guarantee. It terminates owned descendants and fails
closed when a clean group exit was not observed. This retains a necessary execution
boundary without retaining unrelated orchestration.

The Steam runtime recipe was moved to `project_tooling/steam/verify.py` and copied
into the disposable project export as `tools/stage30_verify.py`. It is a project
recipe, not installed framework code. Its Python/PostgreSQL provisioning and socket
access remain necessary for that project's checks. `RoleTestEnvironment` was deleted
only after the direct contained replacement passed.

Historical scripts remain inert and unchanged. Reproducing their old imports requires
the explicit old source closure, not a hidden runtime fallback.

## D. Functional evidence

### Actual native agent executions

There were **five** native CLI sessions: Small, Tester, Implementer, one targeted
Implementer repair and Reviewer. Native structured `thread.started`/`turn.completed`
events, real process exits and captured diagnostics are retained. No banner/session
identity parser, old Controller or Steam workflow driver was used.

| Demonstration | Observed result | Evidence |
|---|---|---|
| Small | One native session changed `src/message.py`; relevant executable check and final scope passed. No Tester/Reviewer. | `native/small-execution.json`, `native/small-decision.json` |
| Medium mechanics | Scoped helper implementation and verification; a later localized fault required one real helper-only repair. Primary re-export stayed unchanged. | `native/implementer-execution.json`, `native/repaired-acceptance.json` |
| Independent Tester | Only public contract and test subtree supplied; no implementation existed. Nine standard-library unittest methods designed independently. | `native/tester-execution.json`, `native/frozen-v1/tests/coverage.md` |
| Tester confinement | Existing private candidate/handoff canary reads denied with errno 2, both in preflight and the actual Tester session. Private bytes unchanged. | `native/tester-denials.json`, Tester trace/coverage |
| Frozen acceptance | Contract, executable tests and coverage frozen before implementation. All nine methods passed against initial and repaired candidates. | `native/freeze.json`, `native/acceptance.json`, `native/repaired-acceptance.json` |
| Implementer confinement | Native Implementer's writable-source profile denied authoritative frozen-test write-open with errno 2. | `post-removal-checks.json` |
| Reviewer evidence | Scoped baseline/candidate, full diff, contract, frozen executable suite, passing output, injected failures and incorrect-oracle evidence supplied. Review accepted with no blockers. | `native/reviewer-execution.zip`, `native/review.json` |
| Reviewer confinement | Candidate/test copy write-open denied with errno 30; authoritative external paths denied with errno 2. Actual Reviewer also observed errno 30. Inputs compared unchanged; candidate/frozen hashes matched. | `native/reviewer-denials.json`, `native/final-decision.json`, `post-removal-checks.json` |
| Final decision | Accepted only after successful required execution, frozen tests, exact scope/integrity checks and actual accepted review. | `native/final-decision.json` |

The medium behavior and strict behavior share the tiny fixture, as permitted by the
compact validation strategy. This is not a new real-repository feature benchmark.
The migration itself was implemented by the native parent with the focused project
checks below. No successful unrelated role was repeated during repair. The example
has explicit individual steps, no run-all operation and no automatic repair loop.

### Deterministic faults, distinct from agent behavior

`faults.py` and the example's `fault` step deliberately injected failures:

- A helper returning its input incorrectly failed the **actual original frozen
  suite**. That failed result remains in `native/fault-acceptance.json`.
- A real native helper-only repair restored passing behavior using the unchanged
  baseline and frozen version. Its complete changed set is `['src/helper.py']`.
- An unauthorized same-directory sibling was rejected despite writable parent
  directory access. Focused regressions also check hidden additions, deletions,
  missing required files, frozen additions/drift, hardlinks and symlinks.
- Malformed `def broken(` bytes, a real exit-17 subprocess and a failed compilation
  were rejected. `rejected-partial.zip` contains the exact rejected bytes after the
  owned source workspace was deleted.
- A separately frozen injected oracle expected 5 for `clamp(5,0,3)` although the
  contract requires 3. Its actual failing result and original version remain
  preserved. It was escalated, not used to change correct implementation or
  silently superseded. The real Reviewer agreed with that diagnosis. It never
  replaced the independent authoritative suite.
- Real timeout execution terminated. An additional real descendant-process test
  verified a surviving owned child is killed and shutdown is reported unsuccessful
  when the clean group exit was not observed.

See `fault-results.json`, `rejected-partial.zip`, `wrong-oracle-v1/`, and
`shutdown-support-tests.xml`. The final focused suite is **12 passed** under WSL,
covering these safety properties rather than preserving the old API test count.

### Direct real project checks

The Steam repository was exported read-only at the same fixed commit used by the
prior engineering evidence:
`0653617666399590c853c39f08e8cf97c9eca45c`.

The exported project's own pinned requirements and existing test fixtures were used.
A disposable PostgreSQL **18.6** instance had no TCP listener and only an owned UNIX
socket. Native filesystem restrictions plus a private user/network namespace
contained direct checks. Neither production `.env` nor ignored production data was
copied. `REQUIRE_DB_TESTS=1` made unavailable PostgreSQL a failure rather than a skip.

- Entire existing pytest suite: **168 passed, zero skips**; JUnit contains **48 actual
  database cases** across schema, query execution and loader idempotency modules.
- Existing Ruff check of `src` and `tests`: **all checks passed**.
- Existing loader replay/idempotency coverage includes SteamSpy, Twitch, IGDB and
  Steam Store outcomes. The existing database fixture performs rollback/connection
  cleanup, and migration tests cover transaction/commit handling. No new transaction
  benchmark or claim of broader atomicity was introduced.
- The unlisted TCP connection probe failed (errno 111) inside the isolated namespace;
  the server's configured socket was actually exercised by the database suite.
- Exported source bytes remained unchanged. PostgreSQL stopped successfully; its
  postmaster PID no longer existed. Both owned runtime/project workspaces were removed.

Authoritative direct-run evidence: `project-direct/result.json`, `results.xml`,
`pytest.json`, `ruff.json`, `network-denial.json` and `runtime-diagnostics.zip`.

The first direct run already passed all 168 tests and Ruff, but its **closeout failed**:
pytest created scratch `*current` symlinks which the strict source snapshot rejected.
That failed run is preserved in `project/`; it is not relabeled successful. The recipe
was repaired to archive scratch without following links, remove only the explicitly
owned scratch subtree, and then verify all source bytes. The second direct run passed
checks, integrity and closeout. This concrete failure justified the one repeat.

### Packaging, integrity and cleanup

The v2 wheel built successfully under WSL, imports directly, and contains exactly
the initializer and two support modules. Source bytes match the final inventory.
Windows pip initially failed to write its sandbox temporary directory; using
workspace-owned WSL build scratch resolved packaging without broadening worker
permissions. Windows also denied link creation for the initial local test attempt;
the final complete safety suite ran under Linux and exercised actual links.

All five native role workspaces were archived and removed. Deterministic fault
workspace cleanup preserved rejected bytes. Both project/runtime pairs were stopped
and removed. Newly generated build/test scratch and package metadata were removed.
Downloaded dependency archives were discarded only after retaining runtime logs,
outcomes and source/test artifacts; they are unnecessary delivery bulk. Pre-existing
user caches, repositories, worktrees and historical scratch were not deleted.

`original-before.json` equals `original-after.json`: HEAD, branch, status, tracked and
nonignored untracked bytes, staged/working diffs, raw index and worktree registry.
Git optional locks were disabled. Ignored production data/credentials were not read.
`historical-integrity.json` verifies **680** unchanged historical files.

## E. Measured simplification

Inventories count physical lines, including comments/blanks. Active-source totals
include installed package and its active drivers before, and package/example/project
recipe after. Tests and Stage 30 evidence scripts are reported separately; historical
source and pre-existing bytecode/cache files are inert, not active runtime inventory.

| Inventory | Before | After |
|---|---:|---:|
| Active source files | 15 | 5 |
| Active source physical lines | 2,208 | 680 |
| Installed package files | 6 | 3 |
| Installed package physical lines | 817 | 296 |
| Test source files / physical lines | 5 / 529 | 1 / 159 |
| Runtime Python dependencies | 1 (`jsonschema`) | 0 |
| Development dependencies | pytest | pytest |
| Custom workflow entry points | 3 | 0 |
| Other custom runtime/control/probe entry points | 4 | 0 |
| Standalone examples / project-specific recipes | embedded in drivers | 1 / 1 |

Operational comparison, counting logical work steps rather than shell invocations:

| Operation | Before | After |
|---|---|---|
| Small | Documented minimum: Implementer → Controller admission/handoff → Tester → generated/frozen harness → acceptance/cleanup (at least 2 native sessions). | Native change → relevant project check → diff/result (1 session). |
| Medium | Task-specific driver and its role/artifact conventions; no proportional medium profile. | Scoped native implementation → relevant verification → final scope/decision; optional review; one repair by default. |
| High-risk | Driver owns role order, normalization/design schemas, generated harness, review receipts and final decision. | Parent chooses Tester → freeze → Implementer → checks → read-only Reviewer → final gate; two repairs maximum by default. |
| Project development checks | Role mailbox client/thread exchanges predefined check names. | Ordinary project pytest/Ruff commands in the provisioned contained environment. |

The strict path retains necessary steps; simplification removes machinery rather
than concealing its guarantees. No token, dollar, quality-comparison or speed-saving
claim is made. See `inventory.json` for file hashes and imports.

## F. Limitations and remaining dependencies

- Strict permissions are demonstrated on installed Linux/WSL CLI 0.160.1. Equivalent
  per-child desktop/Windows confinement is not established. Run denial probes before
  using a different native interface/version; do not assume it is equivalent.
- The trusted native parent still explicitly selects public inputs, required checks,
  review evidence and repair budget. `accept` cannot discover deliberately omitted
  requirements or adjudicate a semantically wrong oracle. No universal policy engine
  was added to attempt that.
- Native auth/model execution remain native. Restricted launches ignore inherited
  user configuration and use native defaults/explicit CLI settings. Environment
  filtering is a selected-variable precaution, not universal credential confinement.
- The owned process helper remains until native cancellation has observed equivalent
  shutdown. Killing a surviving descendant is conservatively reported as unclean;
  successful acceptance requires observed clean shutdown.
- Database provisioning is Steam-owned tooling and requires its Linux packages and
  pinned dependencies. CLI 0.160.1 needs AF_UNIX creation enabled with the owned socket
  and a separate network namespace. This exception is only for deterministic project
  checks, never a network grant to model sessions.
- Real project evidence covers the fixed historical commit, not the current dirty
  original checkout. The latter was intentionally protected and never used for writes.
- No broad engineering-quality benchmark, exhaustive attack proof or runtime-cost
  estimate was performed. The representative boundaries and outcomes above are observed.

These are explicit narrow dependencies, not unresolved failures of the migration.

## G. Usage and rollback

Start with the rewritten [README](README.md). Small work is an ordinary native Codex
request plus relevant project checks. Medium work adds exact scope and final checking.
High-risk work uses the restricted Tester/freeze/Implementer/checks/Reviewer sequence.
The native parent chooses each step and applies repair budgets; successful unrelated
roles are reused. Frozen version corrections require explicit adjudication and a
reviewed new version; the original failed evidence survives.

From WSL, the standalone example is invoked one step at a time:

```bash
python3 -B examples/native_smoke.py /absolute/fresh/evidence small
python3 -B examples/native_smoke.py /absolute/fresh/evidence tester
python3 -B examples/native_smoke.py /absolute/fresh/evidence implementer
python3 -B examples/native_smoke.py /absolute/fresh/evidence evaluate
python3 -B examples/native_smoke.py /absolute/fresh/evidence reviewer
python3 -B examples/native_smoke.py /absolute/fresh/evidence cleanup
```

Project-owned direct verification (use a fresh output directory):

```bash
python3 -B project_tooling/steam/verify.py /path/to/read-only/steam-etl \
  0653617666399590c853c39f08e8cf97c9eca45c /absolute/fresh/project-evidence
python3 -B -m pytest tests -q -p no:cacheprovider
```

Inspect rejected bytes in ZIP `files/` entries, diagnostics in `outcome.json`, and
non-dereferenced links in `links.json`. Every role is preserved before cleanup.
The README documents the small support functions and actual outcome requirements.

Explicit rollback is `docs/stage30-verification/source-rollback.zip`, verified against
`rollback.json` (SHA-256
`d1d34699fdd159e217f5ec642eacf4f66bf713f8d0a967d3c754a6387fe82851`).
Extract the coherent old closure into a separate empty checkout if rollback is chosen.
Do not overlay old/new modules or reactivate historical adapters automatically.

## H. Final verdict

**PASS** — native Codex owns normal orchestration; small work has no mandatory
multi-agent ceremony; strict roles have observed enforced boundaries; frozen tests,
exact final scope, rejected-artifact preservation, targeted repair, direct real
database checks and owned process cleanup work. Obsolete orchestration is deleted,
documentation and packaging describe the actual system, and the original project
and historical evidence are intact.

Final repository state: version 2.0.0; two installed support modules; one standalone
example; one project-specific verification recipe; 12 focused passing regressions;
no active Controller, legacy driver, schema dependency, fallback or replacement platform.
