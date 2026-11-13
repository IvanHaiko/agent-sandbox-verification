# Stage24 — Architecture Cleanup and Consolidation

**Verdict: STAGE24_PASS_ARCHITECTURE_CLEANUP.** Completed 7 October 2026.
No new features, model-routing experiments, OML work or subsequent hardening stage were started.

## A. Before

The repository contained 48 production Python files (8,159 physical lines),
93 non-test validation Python modules, and 70 test files
(28 in `tests/`, 42 in `validation/`). Its README and CLI described older worktree/Docker/custom-transport
architectures. The validated native WSL path lived in the native Linux runner and three validation modules;
the Windows native runner remained experimental. Stage drivers, retry probes, protocol diagnostics,
OAuth/Responses machinery, older orchestration frameworks and generated evidence obscured that boundary.

Inventory and import/reference analysis were recorded before deletion:
[readable inventory](docs/stage24-verification/INVENTORY_BEFORE.md) and
[complete inventory with hashes/import edges](docs/stage24-verification/inventory-before.json).
Every relevant source/test/validation module is classified KEEP, CONSOLIDATE, LEGACY FALLBACK or
HISTORICAL VALIDATION. No original source was irretrievably discarded under DELETE: this checkout
has no Git metadata, so the complete original dependency closure was archived before active-path removal.

The native closure had no dependency on the custom backend. NativeLinuxCodexRunner used standard-library
process/filesystem code; the WSL Controller used that runner and the labels contract; optional roles used
jsonschema and the same Controller helpers. The old package's relative imports were retained together
inside the archive, rather than leaving a partial rollback backend in production.

Before mutation, nine focused guards passed on Windows and WSL. A fresh native baseline used
gpt-6.1-sol / medium, passed 23 frozen cases and removed all three repositories. See
[baseline test record](docs/stage24-verification/baseline-tests.json) and
[live baseline assessment](docs/stage24-verification/before/native-baseline/assessment.json).

## B. Removed

**Removed from active paths; original bytes remain recoverable in the verified archive.**
44 former production Python paths were removed outright. The former `controller.py`,
`roles.py`, `native_codex_linux.py` and package initializer were replaced with the consolidated native
implementation. The active package no longer contains the Windows native experiment, custom transport,
OAuth/Responses/tool relay, Docker runners, old orchestration/approval/persistence frameworks,
telemetry/routing experiments, admission probes or model protocol reconciliation.

Exact removed production Python paths:

- `agent_system/__main__.py`
- `agent_system/agent_transport.py`
- `agent_system/approvals.py`
- `agent_system/architecture.py`
- `agent_system/artifact_execution.py`
- `agent_system/chatgpt_oauth.py`
- `agent_system/chatgpt_plan_transport.py`
- `agent_system/cli.py`
- `agent_system/codex_tool_session.py`
- `agent_system/config.py`
- `agent_system/contexts.py`
- `agent_system/contracts.py`
- `agent_system/errors.py`
- `agent_system/evaluation.py`
- `agent_system/evidence.py`
- `agent_system/experiments.py`
- `agent_system/gates.py`
- `agent_system/git.py`
- `agent_system/hardened_workflow.py`
- `agent_system/independent_tests.py`
- `agent_system/integration.py`
- `agent_system/isolation.py`
- `agent_system/isolation_probes.py`
- `agent_system/live.py`
- `agent_system/mechanical_gates.py`
- `agent_system/model_tool_boundary.py`
- `agent_system/native_codex.py`
- `agent_system/orchestrator.py`
- `agent_system/policies.py`
- `agent_system/responses_http.py`
- `agent_system/responses_lifecycle.py`
- `agent_system/runners/__init__.py`
- `agent_system/runners/base.py`
- `agent_system/runners/chatgpt_plan.py`
- `agent_system/runners/docker_isolated.py`
- `agent_system/runners/isolated_session.py`
- `agent_system/runners/tool_docker.py`
- `agent_system/runtime_observability.py`
- `agent_system/state_machine.py`
- `agent_system/storage.py`
- `agent_system/task.py`
- `agent_system/telemetry.py`
- `agent_system/transport_diagnostics.py`
- `agent_system/workflow.py`

All original validation drivers and validation tests were removed from the active tree. Only the validated
contract/harness and nine relevant guards were promoted, under ordinary names. The old 28 permanent test
files and 42 validation test files were archived; four current test files contain 37 focused test cases.
The obsolete 26 JSON schemas, `.agent_system/models.yaml`, `.agent_system/project.yaml`, old examples,
old `agentctl` entry point, PyYAML dependency and OAuth optional dependency were also removed from active use.

[Exact source/test/validation dispositions](docs/stage24-verification/REMOVED_FILES.md) list every original
module and why it left active source. [Every original file disposition](docs/stage24-verification/file-dispositions.json)
also covers the generated evidence and documents. In total, 2,352 original paths left the active tree;
four production files and the README/build metadata were replaced; `.gitignore` stayed unchanged.

## C. Consolidated

- `artifacts.py` is the single active implementation of candidate/artifact hashing, complete repository
  snapshots, mutation comparison, diffs, owned workspace creation/removal and frozen design/harness/task hashes.
- `native_codex_linux.py` builds native commands once for writable and read-only roles and extracts native
  model/session/provider/error metadata once. Role-specific receipt fields remain explicit.
- `controller.py` contains one handoff → blind design → freeze → deterministic acceptance → cleanup decision
  sequence. It replaces the Stage23 trial driver, removing global output roots, counters and historical gate logic.
- `roles.py` retains the supported structured-output schemas, read-only semantic role execution, review gate
  and Controller canonical-contract verification. Architect and Reviewer reuse the same native runner.
- `validation/labels_contract.py` holds the existing bounded task, Tester-specific instructions, validators
  and harness. The historical task identity was renamed from STAGE20-LABELS to LABEL-NORMALIZATION.
  Criteria, constraints, interface, harness, design/interface validation and failure interpretation are unchanged.
- `validation/native_workflow.py` is one integration driver, with a minimal path and optional full-chain
  preparation/execution. Retry drivers, catalogs, assessment generators and historical prerequisite chains are gone.

Legacy duplicates were removed from active use rather than merged into new generic abstractions. The audit
compares the original and current contract fields and validator/harness ASTs. No production module contains
Stage19–23 naming, experiment task IDs or retry counters. Native permission and workspace ownership names
are now `role_workspace` and `codex-role-*`; their permission/ownership semantics are preserved.

## D. Legacy

There is **no executable legacy package or automatic fallback**. The complete former package, including
74 package files (48 Python modules and 26 schemas), original configuration, tests, examples, drivers and
history is retained only as `docs/history/pre-cleanup.zip`. Manual rollback means extracting into a separate
checkout and explicitly using the former framework. No active import or package-discovery path enters it.

The snapshot contains 2,359 original files. Every entry hash was verified before deletion;
the final archive SHA-256 was verified again. Its size is 8,218,310 bytes, compared with
48,655,877 bytes of original inventoried content. See the
[archive receipt](docs/stage24-verification/archive-receipt.json).

641 final-assessment/evidence files are also expanded under `docs/history/`, preserving the original
relative layout for important Stage20, Stage21/21A, Stage22 and Stage23 records. Earlier/redundant evidence
and source remain compressed. [History index](docs/history/README.md) labels everything historical.
Historical references to early evidence require the full snapshot; they are not current operational instructions.

## E. Current architecture

Controller → fresh native WSL execution → validated workspace artifact → Controller-generated handoff
→ fresh role execution. The default small workflow is Implementer → Independent Tester → Controller
acceptance. Architect and Reviewer are optional. No native Data Auditor is added without a justified task.

Tester sees no candidate, source stub, diff, handoff or conversation history. Its design and Controller
harness are frozen before candidate exposure. Acceptance runs deterministically in a separate read-only
native sandbox, with no additional model/Tester request. Scope, full repository equality, interface,
candidate/design/harness/task hashes, fresh context, native model identity, process shutdown and cleanup
are acceptance requirements. Architect/Reviewer use read-only structured output. Controller alone owns
canonical state and normalization. Native failures remain explicit; they never substitute the old backend.

[README](README.md) is the single current architecture and operation document. The current API is
`agent_system.controller.run_workflow`; the old CLI/configuration/task formats belong to history.

## F. Verification

Final focused results:

| Evidence | Passed | Skipped | Failed/errors |
|---|---:|---:|---:|
| focused-wsl.xml | 37 | 0 | 0 |
| focused-windows.xml | 29 | 8 | 0 |

Commands: `python3 -m pytest -q -p no:cacheprovider --basetemp=/tmp/stage24-focused-linux-final
--junitxml=docs/stage24-verification/focused-wsl.xml` in WSL; the corresponding Windows Python command
used `.test-tmp/stage24-focused-windows-final`. Windows initially exercised unsupported Linux Git cleanup
and Linux absolute-path assumptions; fixture scope was corrected, and those eight Linux lifecycle cases
are explicitly skipped on Windows and pass in WSL. No Windows production backend was repaired or reintroduced.

The tests cover handoff authority, Tester blindness, freeze ordering, all three freeze hashes, deterministic
acceptance, acceptance mutation rejection, native identity/failure/scope predicates, read-only structured
output, schema compatibility, exact Architect scope/criterion validation, review rejection, linked artifact
rejection, cleanup on success/failure, environment filtering and owned Linux process-group timeout handling.

Live native results, all gpt-6.1-sol / medium:

| Workflow | Frozen cases | Controller | Owned workspaces |
|---|---:|---|---|
| before/native-baseline | 23/23 | PASS | Verified absent |
| after/minimal | 24/24 | PASS | Verified absent |
| after/full | 24/24 | PASS | Verified absent |

The post-cleanup small workflow used two fresh role contexts. The full chain used Architect → Controller
normalization → Implementer → blind Independent Tester → frozen acceptance → Reviewer → final decision.
The Controller reviewed all four Architect clarifications and four risks as interpretations of existing
rules, preserving every original task field. Reviewer returned accept with zero blockers/findings.
Both post-cleanup workflows passed 24/24 frozen cases and cleanup. No failed native attempt or retry
was needed. No historical stage experiment was rerun.

| Workflow | Role | Native context | Seconds |
|---|---|---|---:|
| before/native-baseline | implementer | `01a1170d-049e-7352-a5c3-89101bf9f298` | 26.732 |
| before/native-baseline | independent_tester | `01a1170d-6d5c-7561-9102-b11a81f1fccc` | 88.242 |
| after/minimal | implementer | `01a11714-b4d8-7691-b826-d59306a6a1b1` | 25.910 |
| after/minimal | independent_tester | `01a11715-1ac8-7a31-a26d-b049206efa85` | 86.686 |
| after/full | architect | `01a11718-4e03-76e1-8fd7-4a62d427ee11` | 27.537 |
| after/full | implementer | `01a1171a-231c-7903-86ea-6db3815811e6` | 22.784 |
| after/full | independent_tester | `01a1171a-7ce2-70f3-89f8-95c083cd2272` | 65.025 |
| after/full | reviewer | `01a1171b-7cb0-7c31-a175-0b1ac9e926ab` | 28.075 |

Evidence: [small assessment](docs/stage24-verification/after/minimal/assessment.json),
[full assessment](docs/stage24-verification/after/full/assessment.json),
[Controller normalization](docs/stage24-verification/after/full/contract-normalization.json),
[Reviewer](docs/stage24-verification/after/full/reviewer-result.json), and
[final integrity audit](docs/stage24-verification/integrity-audit.json).

The final read-only WSL audit verified eight distinct contexts, all 11 owned repositories absent,
freeze-before-exposure, immutable candidate/task/design/harness hashes, exact routing, read-only semantic
roles, deterministic acceptance, source hashes matching the execution snapshots and the rollback archive.
It performed no new model or acceptance calls. [Executed source](docs/stage24-verification/executed-source.json)
records the exact current source hashes; original source hashes are in the pre-deletion inventory.

## G. Size reduction

| Measure | Before | After |
|---|---:|---:|
| Production Python files, including initializer | 48 | 5 |
| Non-test validation Python modules, including initializer | 93 | 3 |
| Test files, tests + validation | 70 | 4 |
| Physical active production lines, including blanks/docstrings | 8,159 | 638 |

Active production lines fell by 92.2%. After cleanup there
are four substantive production modules plus an initializer, one integration driver plus a contract fixture
and initializer, and four test files. Historical snapshots are excluded from active counts; no surviving
runtime code is concealed in the history count. Counts are reproducible from
[before](docs/stage24-verification/inventory-before.json) and
[after](docs/stage24-verification/inventory-after.json) inventories.

The original inventoried source/docs content was 48.66 MB. The compressed history, expanded important
assessments/evidence and new audit artifacts occupy materially less space (the source/docs tree is about
14.5 MB before this final report). Existing ignored runtime/test caches are excluded from these comparisons.

## H. Remaining debt

- Validation still covers the existing bounded label-normalization contract, not arbitrary repositories,
  dependency-heavy projects or general abnormal-native-error recovery. This cleanup adds no such claims.
- Native execution requires an installed/authenticated Linux Codex CLI and supported permission/schema
  behavior. Future native releases may require compatibility verification; failures currently stop explicitly.
- This checkout has no Git metadata. Manual rollback therefore depends on preserving the verified archive;
  obsolete persisted workflows/CLI formats are historical, not migrated to the native API.

All twelve requested cleanup success criteria are met within the validated bounded workflow.
Stage24 ends here.
