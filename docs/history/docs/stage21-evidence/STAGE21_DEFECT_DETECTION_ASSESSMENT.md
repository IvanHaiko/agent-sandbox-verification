# Stage21 — Independent defect detection assessment

## A. Final result

**FAIL — accepted: false.** Runtime verdict: `FAIL_WORKFLOW_COORDINATION`, at `test_design`.

One real, bounded workflow was attempted. Architect and Implementer completed, but the Independent Tester response ended with **socket_idle_timeout** before a complete structured design was delivered. No test design was frozen, no candidate was exposed to Tester, and neither independent acceptance nor Reviewer ran. Controller rejected final acceptance because the required evidence was missing. This is a workflow/transport failure, not a demonstrated implementation defect, test defect, or capability failure.

Selected task: `src/normalize_labels.py`, with `def normalize_labels(value: str) -> list[str]`. It has ten interacting rules: comma splitting outside quotes; quote removal and concatenation; backslash escaping before syntax interpretation; whole-input errors for dangling escapes/unclosed quotes; ordinary versus protected ASCII whitespace; trim-before-collapse; preservation of protected whitespace; ASCII lowercasing; dropping empty labels; and stable deduplication. Standard library only, deterministic, one implementation file, no external services.

The candidate is preserved but **not accepted or integrated**. Its SHA-256 is `5ab073fdd83200e97d35b51754d7347e8fd3ad893598207306b9d922f340d235`. The retained disposable repository remains at the committed task/stub baseline. The frozen task ID is `STAGE20-LABELS`; the copied prefix is classified below.

[Full task](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/frozen-task.json), [Architect contract](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/architect-result.json), [candidate](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/candidate/initial.py), [candidate diff](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/candidate.diff), [Controller decision](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/controller-decision.json).

## B. Actual workflow

Planned: Architect → Implementer → Tester design/freeze → Controller acceptance execution → optional bounded repair → Reviewer → Controller acceptance.

Actual: Architect completed → Implementer completed → Tester design response failed → Controller rejected acceptance → cleanup completed. Freeze, candidate exposure, acceptance execution, repair and Reviewer were not reached.

| Role | Model / reasoning | Sessions | Model requests | Tool calls | Result |
|---|---|---:|---:|---:|---|
| Architect / Orchestrator | gpt-6-astra / medium | 1 | 1 | 0 | completed |
| Implementer | gpt-5.6-sol / high | 1 | 5 | 4 | completed |
| Independent Tester design | gpt-5.6-sol / high | 1 | 1 | 0 | failed response |
| Tester execution/narration | not invoked | 0 | 0 | 0 | intentionally absent |
| Reviewer | configured gpt-6-astra / medium; not invoked | 0 | 0 | 0 | not reached |

Actual totals: **3 role sessions, 7 model requests, 4 model-selected Docker actions, 0 Controller acceptance executions**. Routing remained the accepted Stage20 routing, verified against the account catalog. Each invoked role had a fresh session, private model home and separate isolated checkout.

Architect took 30.04 seconds; Implementer 118.64 seconds; failed Tester session 67.95 seconds. Runtime-reported numeric total tokens: Architect 7,554; Implementer 41,711; Tester unavailable. Missing Tester usage is not counted as zero. These are workflow-runtime counts; Controller preparation/reporting chat usage is not exposed by this runtime. No monetary estimate or routing benchmark was performed.

[Exact usage and transport observations](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/role-counts.json), [executed driver](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/executed-driver.py), [local driver validation](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/driver-validation.json).

## C. Independent testing value

**Did Tester find a defect missed by Implementer self-checks? Not established.** Tester did not deliver a complete test design. No independent acceptance suite ran, so neither detection nor its absence can be inferred.

Implementer wrote the file once and passed 13 self-chosen cases. These covered quote/escape syntax, protected whitespace, ordinary whitespace normalization, deduplication, empty labels and errors after valid labels. The result is useful self-check evidence, but it does not replace independent testing.

The proposed task has realistic discriminating traps: escaped quotes must not toggle state; quoted commas must not split; protected boundary whitespace must survive trimming; empty quote spans must emit no extra space; malformed suffixes must reject the whole input; and deduplication must follow normalization. Independent testing could broaden confidence in those interactions, but **this run did not demonstrate that benefit**.

Redundant or low-value independent tests: not assessable, because no frozen specification exists. The Stage21 design schema excluded Stage20's immutable-input preservation property. No partial response was reconstructed into tests or substituted with Controller-designed expectations.

[Implementer handoff](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/implementer-result.json), [actual self-check inputs and results](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/implementer-tools.json).

## D. Separation proof

Tester received exactly two explicit bundle keys: `task` and `contract`. It received no implementation, diff, Implementer reasoning/self-checks, Reviewer opinion or previous conversation. Before invoking Tester, Controller verified its implementation file still matched the committed `NotImplementedError` baseline. Tester had no admitted action selectors.

**Freeze before exposure: not completed.** There is no frozen-test hash/receipt because no completed design existed. No `test-freeze.json` or `candidate-exposure.json` was created. Test immutability and candidate hash stability during acceptance cannot be claimed because acceptance never occurred. The candidate's archived hash is recorded separately.

[Exact Tester context](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/test-design-context.json), [final absence/containment checks](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/final-postcheck.json).

## E. Repair flow

Repair-cycle count: **0**. The effective ceiling retained the existing two automatic repair cycles (`agent_system/workflow.py`), with a lower configured usage ceiling honored if present. No implementation/test disagreement occurred; no failure was classified as an implementation defect or a test defect.

No tests, expectations or candidate were altered to manufacture a failure or success. The Controller contract-consistency interpreter was written before the run but was never exercised and never supplied acceptance expectations. Its value and correctness as a classifier were not proven by this experiment.

No role was retried. Existing infrastructure retry configuration remained zero, and the one-workflow receipt prevents automatically restarting the experiment.

## F. Reviewer value

Reviewer was **not invoked**, so it contributed no independent finding or confirmation. There is no Reviewer accept/reject recommendation. Controller explicitly rejected acceptance due to missing frozen tests, deterministic acceptance evidence and review. Invoking Reviewer to narrate the already-known transport failure would not establish implementation correctness.

## G. Anomalies

| Observation | Classification | Material impact and handling |
|---|---|---|
| Tester response socket_idle_timeout | reproducibility issue | Material: prevented structured design, freeze and all later acceptance phases. Recorded as workflow failure; no retry or redesign. |
| Expired prerequisite OAuth credentials | reproducibility issue, resolved | User explicitly requested the usual new browser sign-in. Same account/client verified; credential-store baseline taken afterward. No credentials exported. |
| Initial sandbox access denial for Docker context/old admission | harmless observation | Authorized Controller escalation verified existing admission. No role action escaped Docker or accessed credentials. |
| Synthetic fixture retained scalar expected output | quality issue, resolved before live run | New utility returns lists. Selector rejected the old fixture; corrected fixture passed the 11 focused checks. No live model call or candidate sabotage. |
| Controller interpreter whitespace literal escaping during preparation | quality issue, resolved before live run | Corrected before any role/candidate existed; ordinary/protected tab behavior checked locally. Classifier was not used in the failed run. |
| Legacy task ID prefix STAGE20-LABELS | harmless observation | Copying the Stage20 helper left the uppercase prefix. Same ID stayed consistent across contracts/identities; unique label suffix, Stage21 execution IDs, project and evidence root prevented collision. No evidence mixing observed. |
| completed_function_omitted_from_final | harmless observation in completed Implementer actions | Existing reconciliation admitted validated completed calls; exact Docker actions/results were preserved. No unknown executable or scope escape. |
| nonexecutable_stream_final_mismatch | harmless observation | Nonexecutable protocol discrepancy continued under the accepted policy. Completed Architect/Implementer results validated; no project/evidence mutation from it. |
| nonstandard_or_absent_mime | harmless observation for completed requests | Existing policy tolerated missing MIME. The failed Tester request separately records socket_idle_timeout; MIME absence alone was not treated as failure. |

Tester transport evidence records 32,331 bytes read, `eof: false`, `reader_shutdown_confirmed: true`, `validation_passed: false`, and `body_failure: socket_idle_timeout`. The public session failure was `Codex/model protocol denied`. This evidence establishes an incomplete transport response; it does not establish the upstream cause.

For all observations, no isolation/capability breach or credential/host-state exposure was observed. The idle timeout affected correctness evidence availability and workflow reproducibility; it did not corrupt the archived candidate. Cleanup succeeded despite the failure. Harmless protocol oddities were not automatically converted into security failures, and anomaly counts were not used as metrics.

## H. Efficiency

Stage20 completed with 11 model requests, 6 model-selected Docker actions, 5 role sessions and 2 Tester sessions. Stage21 stopped early with 7 requests, 4 actions, 3 sessions and 1 failed Tester design session. **The lower total is not evidence of improved end-to-end efficiency**, because acceptance and Reviewer were never reached.

The driver removes the second Tester execution/narration session. Deterministic acceptance contains concrete frozen cases and selected invariants and is a direct Controller Docker action. Stage20's second Tester session used two model requests and one tool call. Those narration requests would be avoided if Stage21 reached that phase, but actual successful execution of the new path was not demonstrated here.

Implementer actions were `inspect` → `write` → `check` → `status`: one baseline-file inspection, one source write, one 13-case self-check and one diff check. No repeated unnecessary inspections or rewrite loop occurred. Architect used one compact-contract request and zero tools; Reviewer used none. Architect's 7,554 runtime tokens show noticeable fresh-session overhead relative to a small utility, without evidence of excessive repeated work.

Preparation passed 11 focused checks, including a synthetic-provider real Codex/Docker roundtrip, then 10 local checks after the final harness shape guard. Synthetic fixture correction and preparatory checks consumed no live model requests. The acceptance harness and bounded repair path remain unproven with live independent tests; the unused Controller interpreter added preparatory code without demonstrated value.

## Cleanup and final Controller acceptance

```json
{
  "production_source_unchanged": true,
  "credential_store_unchanged": true,
  "stale_owned_containers": 0,
  "model_homes_removed": true,
  "role_network": "none",
  "host_fallback": false,
  "isolation_preserved": true,
  "docker_cleanup_confirmed": true,
  "disposable_role_storage_removed": true
}
```

The corrected Stage20 cleanup helper removed role/model homes and Controller-owned disposable role runtime, including readonly copied Git storage. No model role was rerun for cleanup. The candidate archive, baseline task repository, handoffs, hashes, Docker ownership receipts and assessment remain as evidence.

Final read-only verification confirmed zero stale owned containers, absent role runtime, unchanged production source/configuration, unchanged credentials since the explicitly authorized reconnection, and a clean baseline repository. Model-selected project code ran exclusively through admitted Docker; host subprocesses were limited to the existing Controller utilities. Signed admission was inherited only after verifying unchanged engine/image/configuration/containment code/Codex and rebinding to the fresh project; no fresh adversarial-probe claim is made.

[Controller assessment](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/assessment.json), [final postcheck](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/final-postcheck.json), [Docker ownership receipts](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/docker-ownership-receipts.json), [production before](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/production-before.json), [production after](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/production-after.json), [credential baseline hashes](C:/Users/4ivan/codex-multi-agent/docs/stage21-evidence/credential-baseline.json).

Stage21 success criteria 1, 3, 4 and 7 were not achieved: no complete end-to-end workflow, frozen design, deterministic independent execution or review. Isolation, no default second Tester call, honest failure classification, impact-based anomaly handling and cleanup were preserved. Final acceptance is **false**.

## I. Next recommendation

Review the single failed-phase idle-timeout evidence before authorizing further work. That demonstrated blocker merits narrow diagnosis; it does not justify architecture expansion, routing optimization, security redesign or conclusions about Tester/model quality.

**Stopped after this one attempted experiment, Controller rejection, cleanup and assessment.** No automatic rerun, additional experiment, OML, Data Auditor, benchmark or Stage22 implementation was started.

