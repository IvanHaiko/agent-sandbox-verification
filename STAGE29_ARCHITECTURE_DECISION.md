# Stage 29 — Architecture decision

**Decision: SIMPLIFY.** Use native Codex for task ownership, role scheduling and repair conversations. Retain narrowly scoped execution boundaries, independent test freezing and one deterministic acceptance check where task risk warrants them. Do not retain the current Controller or task-specific drivers as a general framework.

Executed **9 October 2026**. This stage changes reports/evidence only. It does not implement migration, change the active framework, modify the Steam ETL checkout or start Stage 30.

## 1. Executive summary

The custom framework's useful guarantees are real, but its orchestration is not their source. Native Linux Codex enforces the configured filesystem boundary. The custom code selects inputs, configures that boundary, collects artifacts and checks acceptance. Those responsibilities can survive without the custom role sequence, task normalization protocol or benchmark adapters.

Three focused experiments support this decision:

- **Isolation:** a fresh native desktop child could read candidate/private-handoff/peer-configuration canaries and open a review input for writing. A narrow native Linux permission profile denied the same classes of operations. A directly configured broad-read native profile denied review writes while allowing peer reads. Context separation, read-only access and read confinement are three different properties.
- **Failures:** existing admission checks reject malformed artifacts, unauthorized sibling edits and unsuccessful processes. However, the base Controller deletes rejected candidate bytes during closeout, its failure category is coarse, and the runner falsely rejects an authorized secondary-file-only repair. A valid-looking independent assertion can still be wrong; semantic review remains necessary.
- **Feasibility:** the native parent coordinated three existing restricted CLI role sessions without invoking the custom Controller: blind Tester, freeze, Implementer, frozen evaluation, read-only Reviewer. All **10 acceptance cases passed**, review accepted, and inputs remained unchanged. This is a small architecture proof, not a new engineering-quality comparison.

The recommendation is actionable despite uncertainty. There is no demonstrated quality or cost advantage sufficient to preserve the entire framework. There is also insufficient evidence to remove enforced role boundaries from high-risk work. **Runtime token/dollar savings remain unknown.**

## 2. Prior evidence: what Stages 27–28 establish

Both reports and their delivery ZIPs were inspected. ZIP SHA-256 values match their receipts; all members pass CRC checks. Selected archived decisions, reviews, quality analyses and integrity records were parsed directly. No engineering benchmark was rerun. See [archive audit](docs/stage29-verification/previous-archives-audit.json).

| Dimension | Demonstrated evidence | Decision implication |
|---|---|---|
| Engineering quality | Stage 27: both pass 24 external cases and 168 unchanged regressions. Stage 28: both pass 56 external cases and 168 unchanged regressions. | No established whole-framework quality advantage. Two bounded trials do not prove general equivalence. |
| Context isolation | Native parent requested fresh children; custom roles use fresh ephemeral CLI sessions. Prior native child trace detail is limited. | Keep fresh task-only inputs when independence matters; a separate context is not a filesystem boundary. |
| Filesystem isolation | Custom configured role paths deny tested forbidden reads. Stage 28 native review write-open succeeds twice; custom review gets errno 30. | Retain tested policies, not directory-layout claims. |
| Independent testing | Both Stage 27 suites detect two predetermined defects; both Stage 28 suites detect three incremental defects despite pre-existing bad assertions. | Preserve independent design and frozen tests for consequential work. |
| Review integrity | Stage 28 review catches native shared-UID replay behavior and a custom repair that incorrectly removes distinct Steam links. | Review must compare contract, compatibility and test semantics, not merely count green tests. |
| Failure handling | Stage 27 adapter mishandles scratch symlinks; Stage 28 adapter chooses an unchanged primary target for legitimate repairs. Original failed decisions remain rejected. | These are adapter failures, not evidence that native inference or all framework code failed. Avoid task-specific scheduling/admission machinery. |
| Operating complexity | Both comparisons share `RoleTestEnvironment` and disposable database support; review detail is not fully symmetric. | Prior trials did not prove every custom runtime facility removable. |
| Runtime cost | Timing boundaries/provenance differ; usage counters lack compatible scopes and fields. | No speed ratio, token-saving percentage or dollar estimate is justified. |

Stage 26 also matters: valid engineering output coexisted with failed Tester admission and lost rejected test bytes. Its later collection-before-cleanup correction is specific to `steam_refactoring.py`; it does not repair the base Controller's general failure closeout. Stage 25's success required runtime/setup intervention. These are maintenance and diagnosis concerns, not grounds for another benchmark stage.

Sources: [Stage 27](STAGE27_MULTI_AGENT_BENCHMARK.md), [Stage 28](STAGE28_MULTI_AGENT_BENCHMARK.md), [Stage 26](STAGE26_AUTONOMOUS_REFACTORING_ASSESSMENT.md), and the archived records in [Stage 29 evidence](docs/stage29-verification/REPRODUCE.md).

## 3. Actual architecture inventory and dispositions

The active framework is already much smaller than its pre-Stage-24 ancestor. There is no active custom inference transport, OAuth client, Docker backend, backend plugin system, persistent workflow engine or model router to delete again. Archived code is inert. This workspace has **no Git metadata**. Current role workspaces are independent repositories created with `git init`, not linked Git worktrees.

The active dependency shape is:

```text
native_workflow -> controller -> artifacts
               -> roles -> artifacts / jsonschema
               -> native_codex_linux -> artifacts
steam_workflow -> runner / artifacts / roles schemas
steam_refactoring -> steam_workflow facilities / runner / test_environment
test_environment -> runner.sandbox / artifacts
```

`run_workflow` is the bounded labels path. Steam drivers implement their own sequences; they do not simply configure that Controller. Stage 27–28 adapters add still more task-specific coordination outside the installed package. They are evidence, not production APIs.

In the table, **used** means reachable from a current entry point or demonstrated in retained runs, not proof of ongoing daily usage. Source locations and imports are in [source-inventory.json](docs/stage29-verification/source-inventory.json).

| Component / actual responsibility | Use and failure prevented | Native equivalent / simpler mechanism | Disposition and loss if removed outright |
|---|---|---|---|
| `controller.py:run_workflow`: Implementer → blind Tester → acceptance → optional review; final cleanup-bound verdict | Current labels path; prevents acceptance without required artifacts, passing tests and cleanup | Native parent chooses roles/order; retain one narrow acceptance check | **REPLACE WITH NATIVE** scheduling; **SIMPLIFY** acceptance. Lose mechanical gates if removed without replacement. No generic repair engine exists here. |
| `native_codex_linux.py:__init__, command`: binary/login discovery, ephemeral session flags, model/effort, disabled nested agents | Every current custom role; prevents implicit backend fallback and inherited conversation/config | Installed CLI already owns auth, sessions, model execution | **SIMPLIFY** to explicit native launch settings. Lose repeatable private execution if flags disappear. Do not preserve a Python session abstraction just to rename CLI calls. |
| `permissions, sandbox`: minimal runtime reads, workspace subtrees, no project network/tmp; optional database socket | All role preflights and acceptance; prevents tested peer reads and input writes | Native named permission profiles enforce access | **SIMPLIFY** configuration; keep guarantee. No custom OS sandbox is needed. Removing policy would lose demonstrated boundaries. |
| `_process`: subprocess timeout, process-group termination, captured outcome | Every CLI/sandbox command; prevents a timed-out owned process continuing | Native managed execution where termination is observable; otherwise existing small process helper | **KEEP** narrowly until native cancellation meets the same measured shutdown requirement. Timeout shell launches are insufficient by themselves. |
| `environment`: drops known inherited credentials/chat/app-routing variables | Fresh CLI launches; prevents accidental parent routing and selected credential inheritance | Explicit minimal child environment plus native login | **SIMPLIFY**. It is a selected-variable filter, not complete credential confinement. Never copy auth into role bundles. |
| `run`: writable parent directories, before/after snapshots, exact allowed-file admission, candidate validation | Implementer/Tester; catches sibling-file edits even when a parent directory is writable | Native sandbox plus one full diff check and project validation | **SIMPLIFY / MERGE** scope check into acceptance. Remove mandatory `target in changed` and changed-files-only required-artifact validation; inspect final required files. Lose exact-file protection if only directory permissions remain. |
| `run_read_only`: no writable subtree; native schema/result output; snapshot comparison | Architect/Reviewer; prevents model tools editing inputs | Native read-only profile and `--output-last-message` already do execution/output | **SIMPLIFY** to profile plus integrity check. Output is written by trusted CLI machinery outside model-tool writable roots. A prompt saying read-only is insufficient. |
| `metadata, native_errors`: parse human-readable native banners/usage; sanitize errors | All role receipts; validates identity/resolved model and records diagnostics | Native structured events/results when available, plus concise exit/timeout evidence | **REPLACE WITH NATIVE** event evidence where usable; keep sanitization for retained diagnostics. Drop banner-parser dependence and token-counter interpretation. Do not lose actionable error evidence. |
| `artifacts.py:owned_workspace, cleanup`: home-owned fresh Git repositories, path/link safety, removal | Every custom role; protects original checkout and constrains cleanup targets | Native worktree lifecycle for ordinary implementation; private public-input directories/repos for independent roles | **SIMPLIFY / KEEP** ownership checks. High-risk copies avoid touching the original worktree registry. Native worktrees alone provide no peer-read secrecy. |
| `snapshot, changed_files, artifact_diff, digest, archive, save, require` | Core and Steam paths; detect out-of-scope changes, linked inputs and byte drift | Git diff including additions/deletions/untracked files; hashes only for authoritative artifacts; ordinary files/results | **SIMPLIFY / MERGE** into a small integrity check. Retain safe link handling and before-cleanup collection. Drop repeated complete `.git` byte snapshots for routine roles. Lose reliable provenance if only prose survives. |
| `freeze_design, require_frozen`: validate design, generate harness, hash task/design/harness, exposure receipt | Labels, reused by repository drivers; prevents test drift after exposure | Parent freezes independent executable tests once, records hashes and mounts read-only | **SIMPLIFY** freeze; **REMOVE** task-specific harness generation from framework. Keep executable tests; JSON design need only explain coverage. Hashes detect drift; filesystem policy prevents role writes. |
| Controller Tester input construction and Steam `tester_files` equivalents | Public task/interface/schema, excludes candidate/handoff; Implementer removed before Tester in custom ordering | Fresh task-only native context plus public-only filesystem inputs; design Tester first | **SIMPLIFY** to one public bundle. Keep deliberate omission and denied private reads. Lose actual independence if the candidate/history is supplied through prompt, files or tools. |
| `roles.py:architect_schema, validate_semantic, load_canonical` | Optional full labels path; prevents normalization from changing task fields and contradictory review output | Native parent owns explicit task/clarifications; ordinary structured review with blockers | **REMOVE** repeated task-normalization protocol; **SIMPLIFY** verdict checks. Preserve user criteria explicitly. Fixed arrays/enums and Controller-authored digest receipts are not needed for every task. |
| `semantic_role, review` and Steam review bundling | Optional read-only review; rejects blocker findings, checks candidate/freeze integrity | Native Reviewer in verified read-only session; same contract, full scoped source/diff/tests/results | **REPLACE WITH NATIVE** scheduling; **SIMPLIFY** bundle. Lose an independent compatibility/oracle check if review is removed for high-risk tasks. Base labels review supplies diff/aggregate evidence, not full source/tests. |
| `test_environment.py:RoleTestEnvironment`: request/response mailbox thread for predefined pytest/Ruff commands | Steam Implementer development checks; permits checks while model network stays disabled | Normal project commands in an already provisioned isolated development environment | **REPLACE / REMOVE** mailbox when the same checks run directly. Keep only proven necessary runtime/socket confinement. Until then keep current service; deleting it first removes a demonstrated working test path. |
| `validation/labels_contract.py` + `native_workflow.py`: fixture, oracle, schemas and driver | Current documented bounded demo and offline tests | One small smoke fixture exercising the new path | **REMOVE** labels as a framework task API; retain a small example. Lose demonstration coverage if no smoke replaces it. |
| `steam_workflow.py` + `steam_refactoring.py`: project extraction, duplicated scheduling, handoff/schema checks, acceptance/review/mutations | Stage 25–26 paths; protect original source and run real project checks | Native parent plus project-owned tasks/tests; reuse narrow boundary/integrity functions only | **REMOVE** production drivers after replacement smoke. Preserve historical evidence and required project test commands; no compatibility adapter for old Python APIs. |
| `steam_refactoring.py:preserve_components`: compare old function ASTs outside three authorized loader functions | Stage 26 only; prevents changing existing unrelated function bodies within allowed modules | Task-specific AST check when exact preservation is required, otherwise scoped review and existing regressions | **REMOVE** from general orchestration; keep a project/task check only if still required. Lose exact AST-equality evidence if removed. Its `persistence_sql_unchanged` receipt is broader than its function-only comparison; it does not separately compare every module-level SQL value. |
| `steam_runtime.py`: pinned Python dependencies/PostgreSQL install, socket and teardown | Steam probes/experiments; prevents relying on invisible host packages | Project-owned reproducible environment/CI or the proven existing provisioning recipe | **SIMPLIFY / MOVE** out of orchestration. Do not rewrite package/DB provisioning as an agent platform. Lose real database verification if removed prematurely. |
| `steam_negative_control.py`, `steam_resume_acceptance.py`, `steam_sandbox_probe.py`; Stage 27–28 `experiment.py` | Historical fixed-path control/resume/probe adapters; useful evidence, unsafe as generic importable APIs | Retained reproduction archives, ordinary targeted project checks | **REMOVE** from active entry points/imports; retain immutable historical artifacts. Lose historical reproducibility if evidence itself is deleted. |
| `tests/` (five files), `pyproject.toml`, README, inert history/cache directories | Regression of current machinery; one runtime dependency `jsonschema`, dev `pytest`; archived rollback | A few acceptance smokes, minimal packaging/config and short README | **SIMPLIFY** tests/config/docs after deletions. Remove obsolete normalization/schema/driver tests with their APIs; keep boundary/freeze/failure smoke coverage. History stays inert; old caches are not active architecture. |

**No component is kept because of sunk effort.** The small process helper is provisionally kept because its actual termination behavior is tested. The database/check service is retained during transition because both earlier comparisons depended on it; removal is conditional on a working direct check path.

## 4. Targeted experiments

### A — Context and filesystem isolation

Canaries contained invented text only. All targets existed outside the sandbox. Write probes opened `O_WRONLY` without truncating or writing bytes; hashes stayed equal.

| Execution | Private candidate/handoff/peer reads | Review write-open | What is established |
|---|---|---|---|
| Fresh native desktop child, `fork_turns=none`, inherited current permissions | All three succeed | Succeeds | Parent history was not supplied; ordinary child tools can still reach peer files within shared workspace. Prompt restrictions do not enforce the tested boundary. |
| Direct native named profile, broad root read, workspace read-only | All three succeed | Denied, errno 30 | Native enforcement can supply read-only review without a custom Reviewer implementation; broad reads are still broad. |
| Current runner's narrow Tester profile | All three denied, errno 2 | Denied, errno 30 | Private existing paths are hidden inside the native sandbox; only intended writable test subtree is granted. |
| Current runner's narrow Reviewer profile | All three denied, errno 2 | Denied, errno 30 | Tested private read exclusion and read-only review both hold. |

The first standalone native attempt used the `sandbox_mode` shorthand but omitted this version's required named profile; it exited 2 without running a probe. The corrected explicit-profile result is separate; the failed attempt is preserved. No successful result was overwritten.

The child reported no parent-only sentinel/history in its supplied context. This is an observation consistent with the explicit fresh fork, not a proof against every context/tool leak. Permissions were tested through the actual ordinary child tool and Linux sandbox, not inferred from names such as Tester/Reviewer. See [native child probe](docs/stage29-verification/native-agent-probe.json), [narrow profiles](docs/stage29-verification/experiment-a.json), [direct native profile](docs/stage29-verification/experiment-a-native-explicit.json).

These guarantees are necessary for **deliberately independent high-risk testing/review**, optional for many medium tasks, and unnecessary ceremony for a CSS correction. Their cost is small input/export directories, runtime-readable-path configuration, process lifecycle and a few hashes. Root/parent remains trusted: this is not a host-security certification or confinement of every connector/tool.

### B — Detection, preservation and recovery

Three primary fault classes were exercised: invalid/unsuccessful artifacts, scope violations, and semantically wrong test expectations. Scripted artifact mutations replace only the model process result; real native preflight, current admission checks and base Controller closeout execute. This avoids spending model quota to manufacture mistakes. Actual unsuccessful and timeout processes separately test real shutdown.

| Scenario | Observed detection/classification | Preservation and recovery finding |
|---|---|---|
| Malformed Python artifact | Runner detects `SyntaxError`; rejects. Controller records failed implementation / `required_workflow_evidence_failed`. | Exit/validation receipts and hashes survive; base Controller never archives rejected candidate bytes before deleting workspace. No automatic retry. A future narrow path should collect first and allow a targeted syntax repair. |
| Unsuccessful role leaves valid-looking output | Exit 17 rejects despite valid artifact predicate; actual separate subprocess preserves partial stdout. Real timeout exits -15, marks timeout and confirms process-group ended. | Correctly refuses acceptance on process failure. No provider failure was induced. Retry only the affected role after classifying cause, with preserved partial bytes; no whole-chain repetition. |
| Unauthorized sibling edit in allowed `src/` directory | Sandbox allows directory access; complete snapshot admission rejects `src/unapproved.py` as outside exact file set. | Demonstrates why directory permissions need a final file-scope check. Do not apply rejected diff; require bounded correction or explicit scope clarification. |
| Scope subprobe: authorized helper-only repair | Runner rejects even though every change is authorized, because designated primary target did not change. | Reproduces the underlying fixed-target assumption exposed by Stage 28. It is a false rejection, not a scope violation. Validate final artifacts separately from the set of changed files. |
| Wrong expectation `clamp(5,0,3) == 5` | Shape/syntax-valid design, but correct candidate returns 3. Read-only Reviewer classifies a test-oracle defect and says keep candidate. | Frozen real suite is not edited or bypassed. The injected case is separate evidence. An actual frozen-suite disagreement must stop acceptance until a reviewed, versioned correction or clarification; never repair code merely to make it green. |

The current launcher uses a broad `native_execution_or_artifact_validation` category for different causes; detailed scope and artifact predicates permit diagnosis, but Controller closeout reduces it further. Native orchestration can interpret detailed outcomes and request fixes; it cannot guarantee a semantically correct oracle. Current base code has no retry loop to eliminate; repeated repair orchestration lives in task adapters/native parent conversations. Evidence: [fault results](docs/stage29-verification/experiment-b.json), [oracle case](docs/stage29-verification/b-oracle.json), [Reviewer adjudication](docs/stage29-verification/c-reviewer-result.json).

### C — Minimal architecture feasibility

The native parent chose and invoked each step separately. It did **not** call `controller.run_workflow`, `roles.semantic_role`, the check mailbox or a Steam driver.

1. Tester received only a clamp contract and private-canary paths; no candidate existed. Its own model-tool read attempts returned errno 2. It wrote a 10-case acceptance design in its sole writable subtree.
2. Parent collected the design, generated a trivial fixture harness, recorded task/design/harness hashes, confirmed Tester shutdown and removed its workspace. Generation here is a fixture convenience, not proposed production architecture.
3. Implementer ran in a different private repository; frozen test paths were denied. It produced the candidate after the freeze.
4. Deterministic native sandbox execution passed **10/10**, with no input changes.
5. Reviewer received contract, complete tiny candidate, frozen design, acceptance outcome and separate wrong-oracle evidence. Its native session had no writable input subtree, got errno 30 on candidate write-open, accepted the candidate and correctly adjudicated the faulty assertion. Final hashes matched.

Exactly three restricted native CLI role calls were made, with no role retries/resampling. The separate desktop canary child is not an engineering role in C. Both model output receipts and actual sandbox probes are retained. Existing offline framework checks passed **43/43**.

**Feasibility limit:** this proves native parent coordination of restricted ephemeral CLI sessions while reusing the current low-level runner/artifact helpers. It does not demonstrate per-child policies through this desktop `spawn_agent` API, a newly reduced production helper, dependency-heavy database operation without shared support, or end-to-end automatic repair. The built-in child API here exposes context choice but no policy/workspace argument. A native parent launching isolated native CLI workers is therefore the practical strict mode today; ordinary spawned children remain appropriate where shared access is acceptable. Evidence: [reproduction map](docs/stage29-verification/REPRODUCE.md).

## 5. Native capabilities versus custom guarantees

Installed observations: desktop CLI **0.162.0-alpha.2**; Linux CLI **0.160.1**; Linux `multi_agent` feature enabled. Current custom launches disable nested multi-agent execution. CLI help exposes ephemeral execution, schema/result output and named sandbox profiles. This chat exposes spawn/message/wait/interrupt and native worktree tools, but the child schema does not expose a per-child filesystem profile. No worktree was created for this unversioned framework workspace.

Official documentation describes native orchestration/thread controls, inherited parent policies, optional custom-agent sandbox settings and parent runtime overrides that can reapply those policies. That supports investigating native configuration; it does not establish enforcement in this installed child path. See [official subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents). Version/client differences make a successfully loaded config weaker evidence than a successful denial probe.

| Need | Native already supplies | Narrow custom responsibility retained |
|---|---|---|
| Scheduling, messages, waiting, task context and repairs | Native parent and agent/session controls | None: short workflow instructions and explicit repair budget suffice. |
| Fresh independent role | Fresh context or ephemeral CLI | Select public-only input files and prevent private paths reaching that role. |
| Read/write permissions | Native filesystem sandbox | Configure minimal roots, deny peer inputs, verify representative denial. No new sandbox implementation. |
| Separate editable implementation | Native worktrees or ordinary Git repositories | Only high-risk isolation/export and ownership lifecycle where native worktree sharing is unsuitable. |
| Independent acceptance | Native commands/project test runner | Freeze independent artifacts; check candidate, scope, final results and immutable inputs together. |
| Read-only review | Native read-only permission profile | Supply complete review evidence, verify inputs unchanged; do not assume default child policy narrows. |
| Failure evidence | Native process/events and command output | Preserve rejected bytes before cleanup and retain one concise decision. |
| Database development checks | Project environment and native commands | Temporary existing runtime/socket support until an equivalent direct isolated command passes. |

## 6. Isolation and recovery implications

Independence has two parts: **no inherited implementation reasoning** and **no candidate/private filesystem access during test design**. `fork_turns=none` solves only the first. Test-first ordering removes the future candidate from the environment but does not hide old candidate revisions, another configuration or a stored handoff; narrow reads still matter for strict mode. The reviewer needs readable scoped evidence and zero writable implementation/test inputs. Read-only does not mean unreadable private peer data.

Use three practical outcome classes in the new path: **process/environment failure**, **artifact/scope failure**, and **behavior/review failure**. Keep detailed exit/timeout/validation evidence; do not build a taxonomy engine. For behavior failure, first determine whether the contract, test oracle or implementation is wrong. Freeze changes need a recorded superseding version and semantic review; a contradictory frozen gate remains blocked in its original record.

Preserve candidate/test bytes, relevant diff and process result before any validation-triggered cleanup. Stop timed-out owned processes before reuse. Repair only the affected role/candidate and rerun relevant checks on its final bytes; retain the independent design unless it is explicitly adjudicated incorrect. Escalate unclear requirements, disputed oracle semantics, repeated timeout or failed containment. No silent unsandboxed fallback, whole-chain replay or model substitution.

## 7. Operational complexity and cost

Measured physical source lines (including blank/comment/docstring lines; not quality scores):

| Subsystem | Files | Physical lines |
|---|---:|---:|
| Core: Controller | 1 | 154 |
| Core: native runner/permissions/lifecycle | 1 | 313 |
| Core: artifacts/workspaces/freeze | 1 | 98 |
| Core: semantic roles/normalization | 1 | 118 |
| Core: test-check mailbox | 1 | 133 |
| Package initializer | 1 | 1 |
| **Installed package total** | **6** | **817** |
| Validation task drivers: labels, Steam workflow/refactoring | 3 | 849 |
| Validation runtime, negative control, resume and socket probe | 4 | 380 |
| Labels contract + validation initializer | 2 | 162 |
| **Validation total** | **9** | **1,391** |
| Existing regression tests | 5 | 529 |

There are **five substantive installed components**, **36 class/function definitions including nested definitions/methods**, and **three separately coded active workflow entry paths** (labels and two Steam drivers). Core plus validation is **2,208 lines**, excluding tests, archives and benchmark-specific adapters. The Stage 27–28 adapters are an additional maintenance burden, not included in that active-source total. Source-inventory JSON records the counting method and hashes; no LOC reduction percentage is promised.

Configuration is small in files but broad in Python coupling: six API arguments for `run_workflow`; 12 named inputs for `run`; seven for `run_read_only`; five for `sandbox`; task constants/schemas/callbacks; prepared normalization files; runtime receipts; check-name maps; and per-driver CLI options. These counts include operational inputs, not just user tuning knobs. Model/effort are configurable in `run` but hardcoded in the semantic route; no routing subsystem exists. Python runtime dependency is `jsonschema>=4.18,<5` (with its dependency closure), dev dependency pytest; OS/runtime dependencies are WSL/Linux, Python, Git, native CLI/login, plus project-specific packages/database. There is no active Docker requirement.

The base Controller has four explicit stage labels—implementation, test_design, acceptance, review—plus cleanup and final decision handling. There are two role execution statuses and three candidate statuses. Steam drivers duplicate stage/decision handling; Stage 26 adds baseline and mutation-control phases. These are custom branches, not a persistent state machine. Their exact transition count is path/exception-dependent, so a single grand total would mislead.

Eleven distinct control families recur across source: input/contract validation; runtime/auth prerequisite checks; permission preflight; process termination; session/model identity; mutation scope; artifact syntax/interface/schema; frozen-artifact equality/order; behavioral execution/result agreement; review/verdict consistency; ownership/cleanup. Several are repeated across runner, Controller and task drivers. Consolidate at the boundary where each fact is observed; keep one scope/freeze/final-result check rather than reimplementing these families in every adapter.

Setup today requires installing the package/dev dependencies, Linux CLI and login, selecting a fixture/driver, preparing task/runtime inputs, optionally normalizing Architect output, executing roles and collecting/cleaning evidence. Steam adds pinned environment/PostgreSQL provisioning and an IPC/check service. Small tasks should need only the repository and normal native session; strict mode adds a public test bundle, verified profile and frozen acceptance.

**Essential complexity:** role inputs/permissions, exact changed-file scope, reliable test environment, semantic acceptance, owned process cleanup. **Accidental complexity:** copied task schedulers, fixed primary-target delta admission, Controller-generated task DSL/harness protocols, normalization receipts for unchanged criteria, mailbox service when direct checks suffice, banner parsing and repeated evidence copies.

Current regressions passing does not negate these architectural problems: B reproduces a false rejection and loss of rejected bytes on paths not covered by those successful smokes. No provider failure rate, runtime overhead decomposition, token ratio or dollar cost was measured. Earlier usage counters remain incompatible; Stage 29's tiny fixture does not make them comparable. Avoid claiming savings from source deletion or fewer schemas.

## 8. Operating modes

Choose one of three profiles manually; record the choice in the task brief. No classifier/rule engine.

| Mode | Normal flow | Required controls / repair budget |
|---|---|---|
| **Small** | One native agent edits, runs relevant existing checks and reports diff/result. | No mandatory Tester/Reviewer/isolated sessions. Use ordinary project scope; no new tests for trivial reversible changes unless behavior requires them. |
| **Medium** | Native Implementer in normal checkout or worktree; independent verification when useful; scoped review for meaningful risk. | Explicit allowed files/areas and final diff check. If claiming blind test design, freeze before candidate exposure with fresh/public-only inputs. One targeted repair, then reassess/escalate. Shared-access verification must be described honestly. |
| **High-risk** | Native parent → restricted blind Tester → freeze → separate Implementer → frozen acceptance/regressions → restricted read-only Reviewer → accept/fix/escalate. | Actual denied peer reads and denied review writes; final-artifact hashes; complete review context; preserved failures; at most two targeted repair cycles. Stop on disputed semantics or isolation failure. |

These budgets are proposed operating defaults, not measured optimal values. Task owners may set a different explicit budget. Independent testing and review are paid-for controls selected for concrete risk, not mandatory ceremony.

## 9. Final architectural recommendation

**SIMPLIFY** is selected over KEEP and REPLACE.

KEEP would preserve redundant scheduling and adapter assumptions without a demonstrated engineering-quality or valid cost advantage. REPLACE with only default native children would discard tested guarantees: default shared permissions failed the canary restrictions, and project test-runtime removal is unproven. SIMPLIFY preserves the properties where they prevent observed failures while removing the duplicated policy machinery around native execution.

The practical target is **native Codex orchestration + native sandbox configuration + a small local boundary/acceptance support layer**. Prefer plain configuration/project commands. A helper is justified only for safe private input/workspace creation, terminated-process evidence, collect-before-cleanup and the final scope/freeze check. Do not build another framework around that helper.

## 10. Remaining risks and unknowns

- Strict per-child policies through this desktop API are unproven and not expressible in its exposed schema. Official custom-agent configuration is a possible later implementation choice, not a Stage 29 demonstrated guarantee. Use the tested isolated CLI session path for strict roles.
- The minimal proof reuses the existing 313-line runner and artifact helpers; the proposed reduced implementation has not been built. It establishes removable Controller dependency for this fixture, not a measured final helper size.
- Stage 29 has no database/dependency-heavy candidate. Both previous comparisons relied on shared project runtime support. Retire the mailbox only after equivalent direct contained checks pass.
- Permission profiles depend on installed CLI behavior/runtime paths. A harmless canary preflight is necessary when profile/platform changes; avoid per-command repeated probes or host-wide security policies.
- Semantic oracle errors remain possible with either architecture. A reviewer can miss them; the small clamp example is easier than Stage 28 compatibility semantics.
- Parent/orchestrator is trusted to honor a failing acceptance check. There is no external tamper-proof policy server, immutable evidence store or adversarial-host guarantee, and no such platform is required here.
- Existing daily usage frequency, provider retry counts, true inference time, end-to-end operating-cost savings and native managed cancellation equivalence are unknown.
- Workspace auditing hashes readable files; 65 inaccessible pre-existing historical scratch entries are recorded by stable error markers rather than byte hashes. Active source and original tracked/nonignored project files are readable and separately verified.

These unknowns affect implementation choices and cost estimates; they do not require postponing the simplification decision.

## 11. Smallest viable target architecture

A short future README should describe this entire normal path:

```text
Small: native agent -> relevant project checks -> scoped diff

Strict:
native parent owns task / allowed files / repair budget
  -> fresh restricted Tester: public contract + public fixtures only
  -> collect executable tests; freeze task/tests; end Tester
  -> separate native Implementer: baseline source + project runtime
  -> one acceptance check: final files + allowed diff + frozen tests + regressions
  -> native Reviewer: read-only candidate / baseline / diff / tests / results
  -> accept, targeted repair and recheck, or explicit escalation
  -> collect failures before owned cleanup
```

**Native:** inference, auth, model selection, sessions/context, scheduling, messages/waits, role conversations, normal worktrees and command execution, OS sandbox enforcement. **Custom only where necessary:** public/private input selection and native permission settings; owned-resource lifecycle where native lifecycle is insufficient; frozen artifacts; one deterministic scope/integrity/acceptance check. **Project-owned:** dependency installation, database fixtures, executable tests and CI commands.

Use independent executable tests directly. A small coverage note is enough; no generic test-design schema, framework-generated oracle, task normalization DSL, backend abstraction, universal artifact schema, token collector or evidence service. Retain only task contract, baseline identity, candidate/diff, frozen tests/hashes, relevant process/test outcomes and review/decision; preserve rejected artifacts before cleanup.

For a helper-only repair, compare all changed paths to the allowlist, load required artifacts from the complete final workspace and evaluate behavior. Never require a particular primary file to change. For a frozen-suite oracle correction, retain the failed original version and record a reviewed replacement; never relabel its old run successful.

## 12. Concrete removal order

Detailed objectives, acceptance and rollback are in [STAGE29_SIMPLIFICATION_PLAN.md](STAGE29_SIMPLIFICATION_PLAN.md). The dependency-safe order is:

1. Establish the native-parent execution path using existing profiles, process helper and project checks. Keep current Controller available as an explicit rollback path during this step. Collect rejected bytes before cleanup; validate final artifacts without requiring a primary-target delta.
2. Consolidate public-input isolation, freeze, exact scope and read-only review into the narrow boundary/acceptance path. Replace the optional task-normalization/role schema protocol with native task/review instructions. Prove direct project checks before retiring `RoleTestEnvironment`.
3. Remove `controller.py`, label production driver/DSL, Steam workflow/refactoring/control/resume/probe entry points, role scheduling wrappers and dead tests/imports. Move the necessary runtime recipe to project ownership. Delete old APIs rather than introducing compatibility wrappers. Keep historical benchmark source/evidence inert and reproducible.
4. Remove obsolete schemas/receipts/configuration and redundant packaging dependencies; finish three-profile README and a few meaningful smoke tests. Retain only necessary process/boundary/freeze/scope helpers. Clean only owned temporary resources and confirm original checkout/active migration baseline integrity.

This stage implements **none** of that removal. Stage 29 completes the decision, inventory, focused experiments and migration design. The final integrity/cleanup outcomes are retained in [final-summary.json](docs/stage29-verification/final-summary.json); the compact delivery contains reproducible evidence without repository copies.
