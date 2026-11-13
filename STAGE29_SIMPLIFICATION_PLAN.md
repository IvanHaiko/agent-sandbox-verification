# Stage 29 — Implementation-ready simplification plan

**Selected design: native Codex orchestration with narrowly scoped execution boundaries and acceptance controls.** This is a migration plan only. No migration, active framework change, original Steam checkout change or Stage 30 execution occurs in Stage 29.

The decision and supporting results are in [STAGE29_ARCHITECTURE_DECISION.md](STAGE29_ARCHITECTURE_DECISION.md). The working feasibility proof uses existing restricted native CLI sessions; individually restricted desktop spawned children are not demonstrated. Do not make that unverified capability a prerequisite for the initial migration.

## Target and constraints

Native owns task interpretation, role selection/order, sessions, messages, waiting and repair conversations. Project tools own dependency/database setup and ordinary tests. Retained local support has only these justified responsibilities:

1. Prepare public-only Tester inputs and separate implementation/review inputs; configure native filesystem restrictions.
2. Safely own/clean private workspaces and terminate owned processes when native managed execution cannot establish equivalent shutdown.
3. Collect rejected artifacts before cleanup; freeze acceptance artifacts; perform one final allowed-file, frozen-byte and behavioral-result check.

Use native configuration and ordinary project commands first. Do not create a daemon, task DSL, universal artifact schema, backend adapter API, token collector, new role scheduler or compatibility layer. A helper must implement one of the responsibilities above and have an observed failure it prevents. No new line-count target; reduction should come from removing subsystems.

Keep historical Stage 25–29 evidence immutable and outside active imports. The current checkout has no Git metadata, so before implementation capture a verified, source-only rollback archive outside the active import path or use a separate versioned implementation checkout. Do not alter the original Steam ETL repository, its index or worktree registry while preparing the migration.

## Migration phase 1 — Establish the native execution path

**Objective:** get a usable native-parent path before deleting any mechanism that currently protects execution.

**Affected components:** `native_codex_linux.py` launch/permissions/process functions; `artifacts.py` ownership/collection functions; existing Controller as explicit rollback; project test commands and a short native workflow instruction.

**Expected changes:**

- Parent chooses small/medium/high-risk profile, explicit scope and repair budget. Small means a single normal native session with relevant project checks.
- For strict roles, use the installed CLI's explicit named permissions and ephemeral contexts. Tester sees public inputs plus minimal runtime reads; Implementer sees baseline/project runtime and authorized writable areas; Reviewer sees full scoped review evidence with no writable input subtree. The trusted parent keeps authoritative outputs outside worker writes.
- Prefer native worktrees for ordinary implementation where touching the repository's worktree metadata is authorized. Use independent exported source repositories/private public-input directories for strict roles or protected-original work. Do not treat worktrees as a read boundary.
- Reuse the tested process helper until native execution provides observable equivalent cancellation/shutdown. Keep environment filtering and native login; no auth copying or custom model transport.
- Preserve candidate/test bytes and process outcome **before** validation can trigger cleanup. Use a small task-local evidence directory, not a generalized collector.
- Change retained artifact admission to validate required files from the **complete final workspace**. Compare the full set of changes against allowed paths separately. A valid helper-only repair is allowed; a missing required file or unauthorized sibling edit is rejected. Stop deriving handoff validity from a mandatory primary-target delta.
- Parent invokes existing CLI execution directly; do not copy `run_workflow` into a new scheduler or create a permanent copy of the Stage 29 proof script.

**Acceptance criteria:**

- One small task completes with one native session, proportional checks and no compulsory Tester/Reviewer setup.
- One strict tiny-contract smoke completes Tester → freeze → Implementer → acceptance → read-only Reviewer through native parent coordination, without calling `run_workflow` or a Steam driver.
- Harmless existing canaries establish denied private Tester reads and denied Reviewer write-open; before/after input hashes match. Failure to load or enforce a policy stops the strict path.
- A malformed/nonzero artifact is rejected and its exact partial bytes remain available after owned cleanup; an authorized secondary-only repair is accepted by admission; an unauthorized same-directory file is rejected. These can be variants of one smoke, not a large validation matrix.
- No ignored production data/auth material is copied; original/source baseline integrity is verified.

**Rollback:** select the unchanged old path explicitly using the source-only snapshot/separate checkout. Preserve failed new-path evidence. Never silently switch backend or rerun a successful role to improve its result. Nothing is deleted in this phase.

**Dependency:** must pass before removing the Controller, source drivers, existing process helper or acceptance boundary.

## Migration phase 2 — Consolidate isolation, acceptance and project checks

**Objective:** retain only controls tied to demonstrated failures; remove the need for duplicated role protocols and the check mailbox.

**Affected components:** `artifacts.py` freeze/snapshot/scope functions; `native_codex_linux.py:run/run_read_only` validation overlap; `roles.py` normalization/review protocols; `RoleTestEnvironment`; required subset of `steam_runtime.py`; project test environment.

**Expected changes:**

- Replace framework-generated task-specific harnesses with independent executable tests plus a short coverage note. Freeze task/tests before candidate exposure; record hashes once and provide read-only acceptance copies.
- Consolidate allowed-file diff, required-final-artifact presence, frozen-byte integrity, process completion, test outcome and reviewed blockers into **one deterministic final check**. A nonzero outcome blocks acceptance/application. The native parent interprets it; do not rebuild the old Controller state machine inside it.
- Keep exact-file scope checking: parent-directory write permission does not reject an unauthorized sibling. Include additions, removals and untracked files. Keep safe link handling for owned resources; avoid full `.git` snapshots for each routine role.
- Give Reviewer baseline/candidate scoped source, diff, contract, frozen tests, detailed failures and relevant compatibility checks. Read-only execution and before/after hashes replace special semantic-role scheduling wrappers.
- Replace Architect task echo/enum arrays, normalized-contract digests and mandatory design schemas with a parent-owned task brief and explicit clarification history. Architect becomes an optional native conversation when ambiguity warrants it; it does not confer mutation authority.
- Use three concise failure classes: process/environment, artifact/scope, behavior/review. Preserve detailed underlying errors. One repair default for medium work; two for high-risk; stop earlier on unclear semantics or failed containment. Do not introduce a retry engine.
- Prove pytest/Ruff and actual project database tests run directly in a prepared contained project environment with the same intended access limits. Move the required runtime recipe to project tooling. Only after that proof, retire the mailbox client/thread/request protocol and its `checks` write subtree.
- When a frozen test is semantically wrong, keep the failed original run; require a reviewed, explicitly superseding test/contract version. Do not change correct code solely to satisfy it, omit it from reported results or silently relabel the old run green.

**Acceptance criteria:**

- Existing strict smoke uses executable independent tests and one final acceptance check; frozen tests/candidate remain unchanged during acceptance/review.
- One deliberately wrong expected value is identified as an oracle issue; correct code is not repaired to match it. A failed real frozen gate stays blocked until adjudication is recorded.
- On a disposable project copy, the existing relevant unit/lint and real database checks pass **without** `RoleTestEnvironment`; process shutdown is confirmed. Use a small existing transaction/rollback/replay selection, not a repeat of Stage 27–28 or a new benchmark.
- A targeted repair reuses the frozen independent tests and preserved baseline, evaluates its final bytes, and does not repeat successful unrelated roles. Budget exhaustion produces explicit escalation.
- Reviewer receives detailed enough evidence to assess compatibility; missing DB evidence is reported rather than synthesized.

**Rollback:** keep the existing check service/runtime recipe until direct contained checks pass. If direct DB execution fails, retain that narrow facility and document its remaining dependency; do not weaken permissions or block removal of unrelated schedulers. Restore the prior acceptance path from the source snapshot if a critical gate was lost.

**Dependency:** phases 1–2 together replace the guarantees on which current drivers depend. Do not remove the runtime/check service merely because the clamp fixture passed.

## Migration phase 3 — Delete redundant orchestration and obsolete entry points

**Objective:** remove entire subsystems after their useful effects have working replacements.

**Affected components and explicit actions:**

| Existing component | Action after dependencies pass |
|---|---|
| `agent_system/controller.py` | Delete custom scheduling/final-decision workflow. Acceptance facts already live in the narrow final check; parent owns role decisions. |
| `agent_system/roles.py` | Delete Architect/normalization protocols and semantic-role scheduling/bundling. Retain only a compact review output check if the final acceptance path actually needs it, merged there. |
| `agent_system/native_codex_linux.py` | Remove duplicated artifact admissions, human-banner parsing, role-specific wrappers and hardcoded semantic routing. Retain explicit profile construction/settings and necessary process/diagnostic handling only where direct native tools do not suffice. |
| `agent_system/artifacts.py` | Merge needed private-workspace ownership, collection, freeze and exact-scope primitives into the retained boundary/acceptance support. Delete labels-specific generation/exposure receipts and duplicate snapshot/diff protocols. |
| `agent_system/test_environment.py` | Delete after phase 2 direct-check smoke. If DB confinement still requires a narrow part, retain only that proved necessary part with an explicit remaining dependency. |
| `validation/native_workflow.py`, `validation/labels_contract.py` | Delete as production driver/task contract API; keep one standalone tiny smoke/example under tests/examples. No old `minimal/prepare-full/full` compatibility commands. |
| `validation/steam_workflow.py`, `validation/steam_refactoring.py` | Delete duplicated project-role schedulers and fixed artifact schemas. Keep necessary source export/fingerprint recipe only if phase 1 still depends on it; move that narrow part before deletion. Move the Stage 26 function-AST preservation check into task/project verification only if exact function preservation remains an explicit requirement; do not turn its SQL receipt label into a broader guarantee. |
| `validation/steam_runtime.py` | Move proved necessary dependency/database recipe to project tooling, then remove orchestration imports. Preserve environment/socket restrictions until direct equivalent works. |
| `validation/steam_negative_control.py`, `steam_resume_acceptance.py`, `steam_sandbox_probe.py` | Remove active/importable fixed-experiment entry points. Preserve their frozen historical reproduction source/evidence in existing archives. |
| Stage 27–28 adapters and Stage 29 probe sources | Keep inert evidence only; never promote into the new runtime or delete archival failures. |
| `tests/test_controller.py`, labels-specific `test_acceptance.py`, schema/normalization `test_roles.py`, service `test_test_environment.py` | Remove obsolete API tests with removed APIs; keep only meaningful behavioral boundary/freeze/failure checks. Do not port tests solely to preserve internals. |
| `tests/test_native_launcher.py` | Retain useful containment/process/failure cases adapted to the final boundary; delete tests of removed banner/session wrappers. |
| Package initializer and packaging | Keep only if a retained support package still exists; no empty facade for obsolete imports. |

**Safe removal order:** update active imports/entry points to the working path; move any still-needed source/runtime primitives; remove driver callers; delete Controller/role protocols; delete orphan mailbox and validators; remove tests for deleted APIs. Check the import closure at each deletion group. Historical modules with top-level work must never be imported by the new path.

**Acceptance criteria:**

- Normal small/medium/high-risk execution does not import removed drivers, `run_workflow`, old normalization APIs or benchmark modules.
- Three profile smokes still work, with at most one small deterministic fault variant covering preservation/scope/secondary repair. Strict role denial probes and freeze-integrity checks still pass.
- Real project test commands still work through the phase 2 environment path. No role-specific DSL or hidden old mailbox remains necessary.
- Removed APIs have no compatibility wrappers; import/reference search shows no active caller. No archived source has been reactivated as fallback.

**Rollback:** restore a whole coherent old source closure from the verified source snapshot in a separate checkout. Do not leave half-removed imports or mix old Controller decisions with new evidence. Rollback is manual and explicit; retained native failure never triggers it automatically.

## Migration phase 4 — Finish configuration, evidence and documentation cleanup

**Objective:** leave a small system a developer can understand from a short README and three operating profiles.

**Affected components:** README, `pyproject.toml`, surviving support/test files, stale task schemas/normalization/runtime receipts in active configuration, package discovery and generated scratch.

**Expected changes:**

- Document normal small/medium/high-risk flow, verified permission settings, input boundaries, final acceptance, repair budget and escalation. Clearly distinguish ordinary shared native children from strict isolated CLI sessions.
- Remove unused `jsonschema` dependency only after all surviving production uses disappear; remove obsolete schemas/task-format options and framework tests. Leave project dependencies in their project environment.
- Prefer native structured process/event evidence where available. Retain concise exit/timeout, artifact hashes, test failures and review/decision. Do not add token accounting or recreate previous benchmark log collectors.
- Keep historical archives/assessments immutable and excluded from package discovery. Remove only newly owned scratch/workspaces; old user caches/evidence require explicit ownership and relevance before deletion.
- Retain the process helper only while native managed cancellation cannot meet the observed shutdown requirement. Its removal requires that narrow check, not another architecture comparison.

**Acceptance criteria:**

- README explains the entire normal path without task DSL or internal schema instructions. A developer can run a small task without mandatory multi-agent ceremony.
- Only used configuration/dependencies remain. Source/import inventory confirms obsolete orchestration subsystems and their options are gone.
- Final small/medium/strict smokes pass; final scope/freeze gate, read-only review and partial-output preservation are still demonstrated. Repeat tests only for new changes/failures.
- Source/original integrity and owned-resource cleanup pass. Deliver concise implementation diff and smoke evidence; state any retained DB/process limitation plainly.

**Rollback:** revert this phase's documentation/config/package changes together. Do not remove required runtime dependencies merely to shrink the manifest; source snapshot remains the manual full-architecture rollback.

## Definition of done for the migration

Native Codex owns orchestration. Small tasks use one session. Consequential independent testing and read-only review have **observed** boundaries. Frozen acceptance and exact-file scope are checked once against final artifacts. Failed outputs survive cleanup; repairs are targeted and bounded. Project tests have a working reproducible environment. Custom Controllers, duplicated project schedulers and obsolete protocols are gone, with no compatibility platform replacing them.

This plan proceeds to implementation when requested. It does not require another generic benchmarking stage, a token-accounting system or a permanent Stage 29 proof wrapper.
