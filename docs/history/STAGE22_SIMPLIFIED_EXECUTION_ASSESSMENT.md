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


---

# Stage22 continuation — GPT-6.1 Sol Independent Tester

**STAGE22_CONTINUATION_STOP_MODEL_UNAVAILABLE** — stopped before qualification or any inference.

This continues the preserved Stage22 baseline. The Implementer artifact executor, frozen `normalize_labels` contract and prior evidence were not changed or rerun. The requested account catalog was checked on **2026-10-07 11:37:18 CEST** through the configured ChatGPT-plan transport. [Catalog evidence](docs/stage22-continuation-evidence/catalog.json), [continuation receipt](docs/stage22-continuation-evidence/assessment.json).

## N. GPT-6.1 Sol Tester qualification

The current authenticated account catalog does **not** list the requested `gpt-6.1-sol` route. The known visible routes returned were `gpt-6-astra`, `gpt-5.6-sol`, `gpt-5.6-terra` and `gpt-5.6-luna`. This finding concerns the account catalog used by this system's configured transport; it does not claim GPT-6.1 Sol is unavailable in every application or account.

Qualification attempts: **0**. Consecutive contract-valid designs: **0**. Qualification status: **not run — requested model unavailable**. No reasoning level was selected, no proposed test cases were generated, and schema/contract validity and freezeability are not evaluated. No implementation candidate, previous Tester artifact/error or corrected expectation was exposed to a qualification role. No substitute model was selected and no expectations were rewritten.

The catalog-only prerequisite check initially stopped because the saved OAuth access token had expired. The existing OAuth refresh path successfully restored that connection and verified the same client/account. This prerequisite refresh changed protected credentials; it was not a transport redesign or a role execution. One current model-catalog request then succeeded. Refresh and catalog discovery made **zero inference requests**. [Refresh receipt](docs/stage22-continuation-evidence/prerequisite-refresh.json).

## O. Revised minimal workflow

**0 / 0 trustworthy workflows completed** — none started because the requested model availability gate failed. Previous Stage22 trials were not counted toward the new three-run requirement. There are no new candidate hashes, Tester artifact hashes, Tester retries, acceptance executions or disagreement classifications.

## P. Tester quality comparison

| Tester route | Observed evidence | Interpretation |
|---|---|---|
| Previous Luna low | One design included an out-of-domain Unicode case and a quoted-uppercase expectation inconsistency. | Rejected before freeze/exposure. |
| Previous Luna medium | One accepted minimal flow; one completed flow rejected for a frozen expectation that dropped a literal `b`. | Semantic correctness was not reliable across this tiny sample. |
| Previous Terra medium | One `socket_idle_timeout` before a valid structured Tester artifact. | Semantic quality was not evaluated in that attempt. |
| Requested GPT-6.1 Sol | Absent from the current connected-account catalog; zero design attempts. | No quality comparison or qualification claim is possible. |

This is a comparison of preserved observations, not a general model benchmark. No stronger-model test-generation result was obtained.

## Q. Progressive role restoration

Reviewer: **not reached, 0 runs**. Architect: **not reached, 0 runs**. Full chain: **not reached, 0 runs**. Data Auditor: **0 runs**. Availability failed before Phase A; no later phase was started.

## R. Revised recommendation

Evidence does **not yet support** making `cheap implementation + strong independent testing` the default small-task pattern: GPT-6.1 Sol was not qualified or used. Preserve the accepted cheap Implementer artifact boundary. Resume the requested three-consecutive-design qualification only when this exact model is exposed by the connected account/runtime catalog. Do not substitute Astra or another Sol model, expand roles, or redesign the artifact executor to bypass this stop condition.

## Continuation inference usage and cleanup

| Model | Continuation inference requests | Cumulative Stage22 requests |
|---|---:|---:|
| GPT-6.1 Sol Tester | 0 | 0 |
| Luna (`gpt-5.6-luna`) | 0 | 8 |
| Terra (`gpt-5.6-terra`) | 0 | 1 |
| Other Sol | 0 | 0 |
| Astra | **0** | **0** |

No disposable role homes, workspaces, containers or transfer storage were created by this continuation. Production source/configuration remained byte-for-byte equal to the recorded Stage22 baseline. The protected credential change was confined to the prerequisite OAuth refresh described above; credential values were never exported. Prior diagnostic and accepted candidates remain in their existing separate archives. Only a catalog helper and Controller-owned continuation evidence/assessment updates were added.

Stopped at the requested model-availability condition. No new stage, full-workflow retry, general model benchmark or transport hardening was started.

## Continuation route revision — GPT-6.0 Sol

The user changed the requested Tester model to GPT-6.0 Sol. The current connected-account catalog was checked again on 2026-10-07 11:40:44 CEST. The exact route `gpt-6-sol` is also absent; the only listed Sol route remains `gpt-5.6-sol`. [Current catalog](docs/stage22-continuation-evidence/catalog-gpt6-sol.json), [route revision receipt](docs/stage22-continuation-evidence/gpt6-sol-route-revision.json).

Stopped before qualification under the unchanged availability rule. New qualification attempts: **0**; workflow trials: **0**; inference requests: **0**; Astra calls: **0**. No substitute route or role runtime was used. The accepted artifact executor and previous evidence remain unchanged.


---

# Stage22 continuation — all roles on Sol 5.6 medium

**STAGE22_ALL_SOL56_STOP_QUALIFICATION_FAILED**. The user's latest instruction explicitly overrides the earlier asymmetric route: Implementer, Independent Tester, Reviewer and Architect are configured to use **`gpt-5.6-sol / medium`**. Phase prerequisites remain in place; configured roles are counted as executed only when actually invoked. Astra inference requests: **0**.

The connected account exposes this exact route and effort. [Catalog](docs/stage22-sol56-evidence/catalog.json), [structured assessment](docs/stage22-sol56-evidence/assessment.json). The existing artifact executor and frozen contract were preserved. Historical trials and assessments remain separate and do not count toward this continuation.

## N. Sol 5.6 medium Tester qualification

Fresh independent attempts: **5**. Longest valid/freezable streak: **2**, required: **3**; final streak: **0**. Qualified: **False**. Every context receives only the frozen task/interface/criteria/domain/constraints. No candidate, diff, Implementer output, previous design/error or corrected expectation is supplied. Each attempt uses a new role home and baseline checkout.

| Attempt | Model requests | Cases in complete artifact | Schema valid | Contract valid | Freezeable | Rejection/failure | Cleanup passed |
|---:|---:|---:|---|---|---|---|---|
| 1 | 1 | 0 | not assessed | not assessed | False | socket_idle_timeout | True |
| 2 | 1 | 20 | True | True | True | none | True |
| 3 | 1 | 19 | True | True | True | none | True |
| 4 | 1 | 0 | not assessed | not assessed | False | socket_idle_timeout | True |
| 5 | 1 | 0 | not assessed | not assessed | False | stream_transport_failure | True |

Incomplete transport artifacts are qualification failures, but are **not evidence of incorrect expected values**. Schema and semantics are marked not assessed when no complete design exists. Qualification attempts are bounded by five; no silent route substitution or transport hardening was made. The first failure remains in the record; all remaining authorized attempts used fresh contexts. The final stream failure hit the existing body deadline before validated completion (body_deadline).

The pre-freeze gate checks schema, ASCII domain, unique IDs, nonempty/lowercase/deduplicated expected labels and the empty-input rule. When a complete design arrives, explicit Controller contract reasoning examines every case before freeze. It never executes a candidate as an oracle and does not use the previous Controller task interpreter. Complex disagreements remain frozen evidence for independent execution/review; expectations are never silently rewritten.

## O. Revised minimal workflows

Trustworthy accepted workflows: **0**; operational completions: **0**. Prior Stage22 workflows contribute zero to the new three-run prerequisite. No second Tester narration is introduced. The preserved Implementer path ends at one successful permitted write and receives a Controller artifact handoff; it was not invoked in this continuation.

No revised workflow started: the independent Tester qualification prerequisite did not pass.

## P. Preserved Tester comparison

| Route | Observed result | Supported conclusion |
|---|---|---|
| Previous Luna low | Unicode and quoted-uppercase contradiction | Rejected before freeze. |
| Previous Luna medium | One accepted workflow; one frozen expectation dropped literal `b` | Semantic quality was inconsistent in that sample. |
| Previous Terra medium | Timeout before valid design | Semantic quality not evaluated. |
| Current Sol 5.6 medium | 5 qualification attempts, 2 complete designs | Contract validity observations are recorded above; this is a small sample. |

This is same-task validation, not a general model benchmark. Transport failure is distinguished from test defect and implementation defect.

## Q. Progressive role restoration

Reviewer executions: **0**. Architect executions: **0**. Data Auditor executions: **0**. Full-chain completion: **False**. Roles expand only after the required simpler phases pass; no role is invoked merely to increase agent count.

## R. Recommendation and exact usage

Stop at the failed prerequisite. This run does not establish a reliable all-Sol workflow or justify production routing changes. Keep the accepted artifact boundary; no new stage or unrelated hardening is started.

| Model | New inference requests | Cumulative Stage22 requests |
|---|---:|---:|
| `gpt-5.6-sol` | 5 | 5 |
| `gpt-6.1-sol` | 0 | 0 |
| `gpt-6-sol` | 0 | 0 |
| Luna | 0 | 8 |
| Terra | 0 | 1 |
| Astra | **0** | **0** |

Actual new role executions: **5**. Model-selected tool actions: **0**. Catalog discovery and synthetic admission are not inference. Primary assistant work is outside validation-role counts; no monetary estimate is fabricated.

Source-bound synthetic Docker/Codex admission: **1 passed** (zero live inference). Structural-gate smoke checks passed for a preserved valid design and four invalid variants; no full regression-suite rerun is claimed. Production source/configuration unchanged: **True**. Credentials unchanged during this continuation: **True**. Stale owned containers: **0**. Disposable admission/role storage removed: **True**. [Final cleanup](docs/stage22-sol56-evidence/final-cleanup.json).
