# Stage22 — Simplified execution assessment

**STAGE22_STOPPED_BEFORE_PROGRESSIVE_COMPLETION**

Stage22 replaced the Implementer narration gate with checked workspace artifacts in the explicit simplified execution path. Legacy workflows remain available; this assessment does not claim their default routing was replaced. Validation started with account-listed `gpt-5.6-luna`; repeated Tester design errors led to the next available cheap route, `gpt-5.6-terra/medium`, for Tester only. No expensive fallback was used.

The artifact boundary is an improvement over the Stage20/21 dependency: every Implementer candidate was obtained with one request and one write, with no final-narration request. However, Stage22 did not establish a stable end-to-end workflow: Tester quality and a real pre-artifact timeout blocked three trustworthy minimal trials. Reviewer, Architect and full-chain validation were not reached. **Stage22 overall success criteria were not met.**

## A. Architecture change

Old: model/session handoff → workflow state. New: permitted completed write → exact workspace artifacts → Controller checks and canonical handoff → fresh independent Tester → Controller acceptance.

The Implementer makes one write. The Controller observes the successful Docker action, ends the disposable execution before returning a result that would trigger another model request, closes Codex/relay, and removes the model home. This is normal Controller-directed completion at an artifact boundary; it does not claim the Codex conversation finalized. No final Implementer JSON or prose is required. The Controller then compares the full workspace with its immutable baseline, validates a regular unlinked target, archives exact bytes, records SHA-256 and unified diff, runs the fixed public-interface check in Docker, and confirms no mutation during checking. The candidate remains unaccepted.

Tester sees only frozen task, public interface and acceptance rules. No candidate, diff, Implementer checks, final prose, conversation or hidden reasoning reaches design. A fresh test design is validated and hashed before candidate exposure. Controller generates and executes its harness without a second Tester model session. The untested Reviewer path is configured to receive contract, diff, independent evidence and the Controller handoff; the untested Architect path cannot change the original criteria or interface.

## B. Code changes

- Production: `agent_system/artifact_execution.py` (new). Adds the bounded artifact-ending Implementer execution and Controller handoff builder, including a narrow recoverability allowlist and exact-byte/scope/interface checks. No existing transport, OAuth, Docker, capability, default workflow or routing file was modified.
- Validation: `validation/stage22_workflow.py` (new). Defines gated 3/2/2/1 sequential phases with fresh isolated checkouts/contexts, role-specific structured artifacts, frozen tests, evidence and acceptance after cleanup. It stopped within Phase 1. Reuses existing Stage21 fixed action selectors and admitted transport.
- Validation: `validation/stage22_catalog.py`, `validation/test_stage22_admission.py`, `validation/test_stage22_recovery.py`, `validation/stage22_report.py` (new). Account route discovery, current signed containment admission, supplementary real-Codex/Docker synthetic recovery, and evidence-derived report.
- Tests: `tests/test_artifact_execution.py` (new). Covers normal/no-narration handoff, late transport/schema recovery, unsafe or unknown failure refusal, invalid scope/interface, and mutation during checking.
- Evidence: `docs/stage22-evidence/` and this assessment. Prior-stage source and assessments were preserved. No Git commit or PR is claimed: the shared root is not a Git repository. Trial repositories were disposable.

## C. Phase 1 — minimal trials

Implementer always uses Luna low. Tester initially used Luna low, then Luna medium, and finally Terra medium after the specific invalid designs below. Final minimal trials use the same execution architecture, routes and frozen task.

| Trial | Impl requests/tools | Tester model/effort requests/tools | Execution | Tester reached | Acceptance reached | Workflow / accepted | Cleanup |
|---|---:|---|---|---|---|---|---|
| p1-t1 | 1/1 | — | completed | False | False | False / False | passed |
| validated-p1-t1 | 1/1 | gpt-5.6-luna/low 1/0 | completed | True | False | False / False | passed |
| scoped-p1-t1 | 1/1 | gpt-5.6-luna/medium 1/0 | completed | True | True | True / True | passed |
| scoped-p1-t2 | 1/1 | gpt-5.6-luna/medium 1/0 | completed | True | True | True / False | passed |
| terra-p1-t1 | 1/1 | gpt-5.6-terra/medium 1/0 | completed | True | False | False / False | passed |

**2 / 5 minimal workflows completed operationally overall; 1 accepted. The last cheap-route campaign completed 0 / 1.** One completed flow was rejected for a frozen test defect, so it does not establish trustworthy independent acceptance.

The first preparation attempt used stale pre-Stage21A source-bound admission. It stopped before inference; current admission was refreshed with the existing synthetic adversarial probe prefix. One probe invocation also stopped before containers because its explicit pinned-image environment setting was missing; rerunning with that setting passed. Neither is counted as a live trial.

Initial live trial `p1-t1` wrote and checked a candidate, but the Controller compared a raw Tester baseline hash with newline-normalized text. This false mismatch stopped before Tester. The exact-byte baseline map fixed that concrete Windows bug. Evidence was preserved, with cleanup passed.

Trial `validated-p1-t1` reached fresh Tester, whose low-reasoning design included Unicode despite the ASCII-only contract. It was rejected before freeze/exposure/acceptance. The preserved design also contains a quoted-uppercase expectation inconsistency; no expectation was repaired or silently used. The schema was restricted to ASCII and Tester moved to Luna medium. `scoped-p1-t1` passed. `scoped-p1-t2` completed frozen-suite execution but was rejected: its expected output omitted an ordinary literal `b` from `a\ b  c`. Controller classified this as a test defect; frozen expectations were never rewritten.

Luna test design remained unreliable across low and medium attempts. Only Tester fell back to the next available cheap route, Terra medium. This is a response to a demonstrated workflow blocker, not a model benchmark. Terra timed out before its structured test artifact; validation stopped immediately afterward. No larger role chain was tried. All aborted campaigns and their driver versions are preserved.

Complete per-role counts, reasoning, candidate/frozen-test hashes, statuses, acceptance/review and elapsed times are in [trial ledger](docs/stage22-evidence/trial-ledger.json). Each trial directory retains immutable inputs, tool observations, handoff, design/freeze/exposure, acceptance and cleanup receipts.

## D. Failure recovery

Live abnormal-recoverable executions: **0**. The failed initial trials were Controller/design-contract failures, not model sessions falsely relabeled as successful. Harmless MIME, completed-function omission and nonexecutable stream/final anomalies remain recorded in role observations and were allowed only through the existing validated transport gates.

Normal Implementer completion without model handoff was exercised on every candidate write. Narrow recovery permits a late socket/stream failure or final-handoff schema/finalization failure only after an unambiguous permitted successful write, confirmed shutdown, no security rejection, exact target-only diff, readable archived bytes/hash and passing deterministic interface check. Unknown failures, invalid executable response/tool requests, security/capability failures, absent/corrupt writes and ambiguous mutation/checking stop. Recovery never grants acceptance.

A supplementary **synthetic** late socket-timeout test used real Codex and Docker, one synthetic provider request and one naturally generated candidate write. The failed session receipt stayed failed; Controller built `abnormal_recoverable`, then executed the previously frozen independent suite successfully. No implementation defect was injected. This is a recovery-path check, not a newly observed network outage or an independent live trial. [Recovery evidence](docs/stage22-evidence/synthetic-recovery/result.json).

**Actual live timeout: terra-p1-t1 / test_engineer.** Model gpt-5.6-terra/medium; requests 1; tools 0; execution status `unrecoverable`. EOF observed: False; reader shutdown confirmed: True; handoff status: failed. No frozen Tester artifact existed, so this semantic role was unrecoverable. The checked Implementer candidate remained archived and unaccepted. No hidden network cause or successful test design is inferred. [evidence](docs/stage22-evidence/terra-p1-t1/role-counts.json)

## E. Phase 2 — Reviewer

Not reached. The preceding layer did not satisfy its stability gate; no role/workflow claim is made.

## F. Phase 3 — Architect

Not reached. The preceding layer did not satisfy its stability gate; no role/workflow claim is made.

## G. Full multi-agent trial

Not reached. The preceding layer did not satisfy its stability gate; no role/workflow claim is made.

Largest actually exercised chain: Implementer → Controller artifact handoff → fresh independent Tester design/freeze → Controller deterministic acceptance. One candidate was accepted; a second completed flow was rejected for a frozen test defect. No Reviewer, Architect or Data Auditor execution occurred.

## H. Model usage

- **Astra calls = 0**.
- Sol calls = 0.
- Luna calls = 8; exact route `gpt-5.6-luna`.
- Terra calls = 1; exact route `gpt-5.6-terra`.
- Total cheap-model calls = 9.
- Live role executions = 9; live model requests = 9; model-selected Docker actions = 5.
- All non-Tester roles use Luna low. Tester used Luna low once, Luna medium twice, then Terra medium in the final campaign. No Sol/Astra inference, routing benchmark or expensive fallback.
- Catalog discovery is separate from inference. Synthetic admission/recovery provider requests are local fixtures and do not count as live model calls. Primary assistant implementation work is outside the validation-role accounting. No monetary cost estimate is fabricated.

## I. Operational reliability

Total live trials: **5**; completed operational flows: **2**; accepted candidate artifacts: **1**; unrecovered workflow failures: **3**; completed but rejected flows: **1**; live recoverable abnormal executions: **0**; live Tester design runs: **4**; deterministic acceptance runs: **2**. The completed rejected frozen-test-defect trial blocked role expansion despite operational completion. Initial failures remain in these totals. Every independent trial used fresh role contexts and workspaces; no implementation history was reused. The supplementary synthetic recovery uses an explicitly reused frozen design and is counted separately.

This small same-task sample supports feasibility and an operational simplification; it is not a statistical reliability guarantee or proof of defect detection. Independent suite results govern correctness; passing artifacts are promoted only after optional review and verified cleanup.

## J. Complexity removed

- Mandatory final Implementer narration/structured model handoff in the simplified path.
- Returning the terminal write result solely to trigger another narration request.
- Implementer baseline inspection, repetitive diff inspection and model confirmations of Controller-known facts on this frozen task.
- Architect and Reviewer as mandatory roles for the minimal small-task path.

Controller execution of frozen tests without second Tester narration was already present in Stage21 and was retained, not newly credited as removed. No generic bus, workflow DSL, new policy engine, scheduler/database, retry platform, OAuth or transport rewrite was added.

## K. Remaining weaknesses

Transport must still deliver and validate the initial executable write response and each semantic role artifact. Artifact recovery does not rescue a pre-write outage, invalid command/identity, scope violation, corrupt candidate, failed interface/check infrastructure or unconfirmed shutdown. Tester still needs a schema-valid, in-scope frozen test specification; Reviewer needs a valid recommendation and rationale; Architect needs an exact contract refinement. Semantic roles are not blindly recovered from the presence of arbitrary files.

Cheap Tester design initially produced an out-of-scope case, an incorrect quoted-uppercase expectation and a frozen incorrect literal-preservation expectation. Frozen expectations are never rewritten after exposure; a future conflicting expectation must be reported as a test defect. Terra fallback does not establish broad independent test quality. The artifact executor ends intentionally after one successful write, so it is appropriate for a bounded single-file pass; general incremental implementation, repair loops, large tasks and Data Auditor remain unvalidated. Legacy production flows still have their prior handoff rules unless this explicit new path is selected.

## L. Recommended production workflow

Do not finalize adaptive production routing from incomplete evidence. Keep the bounded artifact path opt-in; stop role expansion at the failed simpler layer.

## M. Next step

Stop here. The smallest justified next investigation, only if requested, is one contract-only cheap Tester design/freeze check once the transport is usable, focused on correct expected outputs. Do not expand roles or claim production routing until three trustworthy minimal trials exist. The Implementer artifact boundary already worked and needs no new protocol to address these observed Tester blockers. No Stage23, OML work, broad model benchmark or unrelated hardening was started.

## Verification and cleanup

Final stale owned containers: **0**. Credential store unchanged: **True**. Stage22 temporary roots removed: **True**. [Final cleanup](docs/stage22-evidence/final-cleanup.json).

Focused checks: **95 passed, 1 skipped** (the previous Stage21 disposable runtime was already removed). Current source-bound synthetic admission: **1 passed**. Real-Codex/Docker synthetic late-timeout recovery: **1 passed**. The broader default regression run was interrupted after the stop condition; no full-suite pass is claimed. [Check manifest](docs/stage22-evidence/checks.json).

