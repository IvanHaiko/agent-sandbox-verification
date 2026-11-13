# Stage23 — Native Codex Execution Backend Assessment

**STAGE23_PASS_NATIVE_BACKEND — smoke 3/3, minimal 3/3, Reviewer 2/2, Architect 2/2, full chain 1/1.**

On 2026-10-07, supported native WSL Codex completed every required gate using the exact requested model. The Architect blocker was diagnosed as a rejected native output schema: array-valued `const` in `allowed_mutation_scope`. The request schema now uses scalar enums and array lengths; Controller separately enforces exact ordered interface/scope/criteria/constraints equality. Requirements, model, permissions and transport did not change.

Three failed Architect launches remain recorded: the first two lost their native error text; the later diagnostic failure preserved `invalid_json_schema`. Successful trials were retained without rerunning them. After the bounded schema repair, Architect-2 and one fresh complete chain passed. This is bounded native-backend validation, not proof of arbitrary-project reliability or lower cost. Production defaults remain intact. Stage24 was not started.

Historical assessments are preserved in `INITIAL_WINDOWS_ASSESSMENT.md`, `SMOKE_GATE_ASSESSMENT.md`, `MINIMAL_GATE_ASSESSMENT.md`, `PRE_RETRY_PARTIAL_ASSESSMENT.md`, and `PRE_SCHEMA_FIX_ASSESSMENT.md` under their existing evidence directories. Original failed attempts, diagnostic runs and completed trial archives remain recoverable.

## A. Native Codex discovery

- Ubuntu 26.04 LTS WSL2, kernel `6.6.87.2-microsoft-standard-WSL2`, Linux user `ivan`.
- Native `codex-cli 0.160.1`; `/home/ivan/.local/bin/codex`, resolving to the installed standalone Linux release.
- Native Linux ChatGPT sign-in and supported login status previously passed; no credential copying, OAuth parsing or API-key transport was introduced. Native Codex owns authentication.
- `codex debug models` exposes `gpt-6.1-sol`. All successful roles have exact model/provider/session banner evidence plus validated native-produced artifacts; provider `openai`.
- Fresh `codex --no-daemon -a never exec --ignore-user-config --ephemeral --color never --cd <repo> --model gpt-6.1-sol ... -` with stdin role input. No resume/fork/history. Effort `medium` for every workflow role; prior three smoke trials used `low`.
- Read-only Architect/Reviewer results use documented `--output-schema` and `--output-last-message`, written by native CLI to Controller evidence outside the role workspace. Native narration/reasoning is not workflow state.

## B. Architecture

```text
fresh Architect (where selected; read-only)
  → Controller reviews proposal and freezes canonical original contract
  → fresh Implementer edits sole permitted module
  → Controller hashes/diffs artifact and creates handoff
  → fresh independent Tester receives contract/schema only
  → Tester design validated, frozen and hashed; Tester exits and is cleaned up
  → Controller exposes candidate to a separate read-only native acceptance sandbox
  → fixed frozen harness executes; Controller checks result/scope/hashes
  → fresh read-only Reviewer receives contract, diff and Controller evidence
  → Controller final decision → checked cleanup
```

Native Codex owns inference, authentication and tool lifecycle. Controller owns canonical contract, artifacts, orchestration and acceptance. No custom plan transport, relay, proxy, model protocol, Docker around inference, model-generated handoff authority or extra Implementer/Tester narration session is needed. Supported [non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode) and [permission profiles](https://learn.chatgpt.com/docs/permissions) remain the runtime interfaces.

## C. Changes

The opt-in `agent_system/native_codex_linux.py` launcher retains native error diagnostics, including safe fields from multiline JSON errors. `validation/stage23_wsl_continuation.py` adds bounded Reviewer/Architect/full gates, immutable executed-source archives, separate evidence roots and required failure receipts. Its Architect request schema no longer contains array-valued constants; local equality checks preserve the original stronger semantic contract. `validation/stage23_wsl_workflow.py` has explicit hooks for normalization and read-only review; the existing handoff/blindness/freeze/acceptance sequence is preserved.

One focused schema guard checks changed scope/criteria plus reordered/duplicated criteria. The latest debugging phase ran only that guard, rather than the full suite. Hash/receipt audits read completed artifacts without executing tests or inference. New evidence resides in `docs/stage23-wsl-evidence/continuation-schema-fixed/`; prior `continuation`, `continuation-retry-1` and `continuation-diagnostic` archives remain intact. Architect-1's completed workflow is preserved with its own original source snapshots. Existing production transport/routing, Windows sandbox and authentication configuration were not changed. The project root is not a Git repository; no commit/PR is claimed.

## D. Smoke trials

**3/3 PASS**, preserved without restarting. Three isolated fresh native executions implemented the exact `add_one` module, changed only `src/add_one.py`, and removed their repositories. Candidate SHA-256: `cbb9d566186943a504d0d8de0ff291eb4bcbc753fd36505065470d3f8e395565`. [Original summary](docs/stage23-wsl-evidence/smoke-summary.json). The Stage23B prerequisite is separate and not counted among these trials.

## E. Minimal multi-agent trials

**3/3 PASS**, preserved without restarting. Six fresh native Implementer/Tester contexts, 70/70 independent frozen cases (24, 23, 23), Controller-owned handoffs/acceptance, nine removed repositories. [Original summary](docs/stage23-wsl-evidence/minimal/summary.json) and original integrity/contract-consistency audits remain unchanged. The bounded ASCII `normalize_labels` contract is the same original task in all later workflows.

## F. Reviewer trials

**2/2 PASS.** Original Reviewer gate: 46/46 frozen cases, read-only results, no blockers/findings or changed decisions. See section O. Reviewers in both Architect workflows and the full chain also completed normally and recommended accept.

## G. Architect trials

**2/2 completed workflows PASS**, with recorded failed setup attempts and a schema repair. Architect-1 was completed once; its artifacts were reused as evidence. Architect-2 was rerun only after its exact deterministic request-schema rejection was established. See section P.

## H. Full workflow

**1/1 PASS**, fresh Architect → Controller contract → Implementer → handoff → blind Tester/freeze → deterministic acceptance → Reviewer → Controller decision → cleanup. No planted defect or Data Auditor was needed. See section Q.

## I. Model use

| Model | Successful Stage23 native role executions |
|---|---:|
| gpt-6.1-sol | 27: 3 smoke, 8 Implementer, 8 Tester, 5 Reviewer, 3 Architect |
| Astra / GPT-5.6 Sol | 0 |

Three additional failed Architect launches are recorded separately; successful inference responses were not established for those launches. Stage23B separately completed one native prerequisite execution. Catalog, diagnostic and Controller acceptance commands do not count as model executions. Internal native request counts, tokens and monetary cost were not measured. All 12 resumed successful role contexts are fresh and distinct from prior successes and failed launches.

## J. Failure and repair

The later failed Architect-2 session `01a116a3-bb8c-7832-981a-de5a7f7a620e` exited 1 after 2.470 seconds. Native error:

> Invalid schema for response_format 'codex_output_schema': context=('properties', 'allowed_mutation_scope'), Unexpected constant value: ['src/normalize_labels.py'].

Code `invalid_json_schema`, type `invalid_request_error`, parameter `text.format.schema`. Classification: **invocation/configuration — native output schema**. Sandbox preflight, scope, process shutdown and cleanup passed; this diagnostic failure was not an authentication or Windows sandbox failure. The first two missing diagnostics cannot be retroactively reconstructed. One earlier native launch accepted the original schema; this does not override the explicit rejection observed later.

Repair: replace array-valued `const` with scalar enums and fixed lengths for scope/criteria/constraints. Controller post-validation then compares the complete ordered lists and interface to the frozen original. Reordering, duplication, additions and substitutions remain rejected. The canonical task stays Controller-owned. Supported [Structured Outputs guidance](https://developers.openai.com/api/docs/guides/structured-outputs) documents a subset of JSON Schema; local native errors establish the specific compatibility problem here.

[Schema repair receipt](docs/stage23-wsl-evidence/continuation-schema-fixed/schema-repair.json) preserves the exact rejection, schema hashes and successful corrected Architect. Earlier diagnostic-loss handling was repaired; native error receipts now retain message/type/code/param without arbitrary stdout, reasoning or authentication data. The latest debugging phase ran one focused guard (expanded on its second run), with no full suite or repeated accepted smoke/minimal/Reviewer trials. Historical nine-test evidence is separate. A known setup correction succeeded; arbitrary runtime-error recovery is still not demonstrated.

## K. Isolation and cleanup

Every live role uses a fresh WSL repository and ephemeral native context. No resume, fork, shared conversation history, inherited API credentials or app pipe is used. Authentication remains native-owned outside role inputs. Native permissions retain minimal runtime reads and the installed release directory, bounded role workspace reads, `src` writes for Implementer, `tests` writes for Tester, no writes for Architect/Reviewer, project network disabled and `/tmp`/`TMPDIR` denied. No `:root` grant, full-access mode, sandbox bypass or Windows permission expansion was added.

Native preflights and exact complete repository comparisons include Git metadata and reject linked entries. Tester has no candidate/stub/handoff before freeze; the candidate reaches a separate Controller acceptance repository only after Tester shutdown. Frozen task/design/harness and candidate hashes stay unchanged. Architect/Reviewer repositories remain read-only; Controller owns their output archives. All 38 WSL repositories created across Stage23 gates and attempts are independently verified absent; Stage23B is separate. This checks the bounded repository/workflow scope, not every native-runtime write on the host.

[Final integrity audit](docs/stage23-wsl-evidence/continuation-schema-fixed/integrity-audit.json) verifies all 12 resumed contexts, 15 completed-workflow repositories, all 38 historical/current repository absences, canonical equality, freeze ordering, candidate/test hashes, independently consistent frozen expectations and original source snapshots. It executes no model or tests.

## L. Complexity comparison

The tested WSL path removes Controller ownership of custom inference/auth/tool protocol while retaining explicit artifact orchestration. All required gates now complete using native Codex, without a custom transport. The old and native samples use different models and are not a controlled speed/cost/reliability comparison. Extra Architect/Reviewer contexts add observable latency without demonstrated causal quality improvement on this explicit bounded task.

## M. Backend recommendation

Prefer native WSL Codex for the validated bounded native workflow. The complete Stage23 gate supports the native execution architecture; arbitrary workloads, dependency-heavy projects and broad abnormal recovery need separate evidence. This stage implements no production-wide migration.

## N. Role routing

Use the observed exact `gpt-6.1-sol / medium` route for workflow roles. No cheaper routing, Astra or GPT-5.6 fallback was introduced. Smoke's historical `low` effort remains its own completed evidence. Role-value recommendations are in section S.

## O. Reviewer gate

**PASS 2/2**, fresh Implementer → handoff → blind Tester → freeze → acceptance → Reviewer → Controller decision. Reviewer receives only contract, diff, Controller handoff, frozen-test summary/results and scope/interface evidence, without prior conversations.

| Trial | Reviewer route | Session | Recommendation | Blockers / findings | Frozen cases | Controller | Seconds |
|---|---|---|---|---|---:|---|---:|
| reviewer-1 | gpt-6.1-sol / medium | `01a11667-d4e9-79b0-bc32-793c8290d850` | accept | 0 / 0 | 24 / 24 | accept | 19.756 |
| reviewer-2 | gpt-6.1-sol / medium | `01a1166a-041c-7862-9fb0-de94ddae210e` | accept | 0 / 0 | 22 / 22 | accept | 13.616 |

Both read-only reviewers provided limited static rule-interaction corroboration. **Zero novel material findings, zero changed decisions.** Mean extra Reviewer latency was 16.686 seconds and one native role execution per workflow. Internal request/cost counts are unknown. Later three Reviewers likewise added no blockers/findings. No planted defects were used, so defect-detection sensitivity is not measured. [Original Reviewer summary](docs/stage23-wsl-evidence/continuation/reviewer/summary.json).

## P. Architect gate

**PASS 2/2 after bounded schema repair.** Each completed workflow used fresh native contexts for Architect, Implementer, blind Tester and Reviewer, with Controller-owned canonical contract, handoff, acceptance and final decision.

| Trial | Architect session | Architect seconds | Clarifications / risks | Frozen cases | Controller | Cleanup |
|---|---|---:|---:|---:|---|---|
| [architect-1](docs/stage23-wsl-evidence/continuation-schema-fixed/architect/architect-1/assessment.json) | `01a1169f-b55e-7973-9b59-43ff96a8bc9e` | 25.027 | 4 / 4 | 23 / 23 | accept | all 5 removed |
| [architect-2](docs/stage23-wsl-evidence/continuation-schema-fixed/architect/architect-2/assessment.json) | `01a116a5-2fa9-7a30-92b2-a72cea53217e` | 26.415 | 4 / 5 | 22 / 22 | accept | all 5 removed |

All roles used `gpt-6.1-sol / medium`. Architect saw only the original task plus its output schema/instructions. Controller reviewed each clarification/risk, preserved every original criterion/constraint/interface/scope field and selected no code or algorithm recipe. No proposed requirement broadened the contract.

Architect-1 summarized escape/quote precedence, whitespace provenance, lowercasing protected letters, final-string emptiness/deduplication and whole-input errors. Architect-2 also made explicit that removed empty quote delimiters do not themselves break ordinary-whitespace runs. These are useful compact interpretations of existing rules, **mostly duplication of an already explicit contract**. Risks were in scope but no novel material risk was established. Both implementation/test portions passed (23 and 22 cases); earlier minimal workflows already passed, so improved quality cannot be attributed to Architect. Mean Architect gate overhead: **25.721 seconds**, plus one extra native role execution per workflow. This sample does not justify mandatory Architect use for every task.

Failed launch history is retained: initial Architect-1 and its explicit retry lost diagnostic text; later Architect-2 failed with the exact array-constant schema rejection. That confirmed harness/configuration error justified the narrow repair/retry. Architect-1's accepted workflow was copied as evidence with its executed-source snapshots and was not run again. Architect-2 and the full chain use the corrected schema. [Final Architect summary](docs/stage23-wsl-evidence/continuation-schema-fixed/architect/summary.json), [repair](docs/stage23-wsl-evidence/continuation-schema-fixed/schema-repair.json), and per-trial normalization/marginal-value receipts record this distinction.

## Q. Full-chain trial

**PASS 1/1.** Fresh Architect → Controller-normalized contract → fresh Implementer → Controller handoff → fresh blind Tester → freeze → Controller deterministic acceptance → fresh read-only Reviewer → Controller decision → cleanup. All original criteria remain unchanged. No planted defect, Data Auditor, extra narration session or prior conversation was used.

| Role | Route | Native session | Seconds | Exit | Result |
|---|---|---|---:|---:|---|
| architect | gpt-6.1-sol / medium | `01a116a8-f920-71d1-9b91-a6af88c0eac2` | 26.399 | 0 | completed |
| implementer | gpt-6.1-sol / medium | `01a116a9-ef09-7011-89ae-99c5ddd73475` | 28.538 | 0 | completed |
| independent_tester | gpt-6.1-sol / medium | `01a116aa-5f2d-70f1-b9f4-194ec7cef639` | 113.908 | 0 | completed |
| reviewer | gpt-6.1-sol / medium | `01a116ac-1dde-7123-a33c-be6b87ceba36` | 24.929 | 0 | completed |

Frozen cases: **24/24 PASS**; interface/properties/scope/hash checks passed. Reviewer recommended accept without blockers/findings; Controller accepted after cleanup. Candidate SHA-256 `e1f416b51aca5c0af13f8e1e054463b124bf77a42188dafedb2b4d8196cf1809`. Frozen design SHA-256 `d2e0a667124e2a7da3a4d5b4f552f1774f2dfad680522e48259dd7a80c0d22c7`. All five repositories were removed. [Full assessment](docs/stage23-wsl-evidence/continuation-schema-fixed/full/full-1/assessment.json) and [Controller decision](docs/stage23-wsl-evidence/continuation-schema-fixed/full/full-1/controller-decision.json).

## R. Final Stage23 verdict

**`STAGE23_PASS_NATIVE_BACKEND`.**

| Required gate / invariant | Evidence |
|---|---|
| Smoke | 3/3 PASS, preserved |
| Implementer → blind Tester | 3/3 PASS, preserved; 70 frozen cases |
| Reviewer | 2/2 PASS; 46 frozen cases |
| Architect | 2/2 completed workflows PASS; 45 frozen cases; setup failures disclosed |
| Fresh representative full chain | 1/1 PASS; 24 frozen cases |
| Exact model and fresh native contexts | gpt-6.1-sol / medium for all workflow roles |
| Tester blindness/freeze, read-only Reviewer, Controller canonical state | independently audited |
| Artifact/hash recovery and cleanup | passed; all 38 Stage23 WSL repositories absent |
| Custom transport required | no |

Across accepted workflows **185/185 frozen cases passed**. The final native gate succeeds after a documented schema compatibility correction; failed attempts are not erased or counted as successes. [Final Controller summary](docs/stage23-wsl-evidence/continuation-schema-fixed/final-summary.json). This is the bounded Stage23 conclusion, not a statistical production reliability estimate.

## S. Recommended production role structure

For small bounded tasks, prefer **Implementer → independent Tester**, with Controller handoff/freeze/acceptance/decision/cleanup. For medium tasks, use that simpler sequence provisionally and add Architect when contract interactions or uncertainty warrant clarification; add Reviewer when independent static review has a concrete purpose. The four-role chain is now operationally validated, but this task does not establish that it should be mandatory: Architect largely restated explicit rules and Reviewer made no novel finding or changed decision. Medium-task complexity itself was not independently sampled. Keep the exact observed model route until a separately authorized routing study.

## T. Backend recommendation

**Native WSL Codex should become the preferred backend for the validated native workflow.** Retain the old custom transport intact as a legacy fallback/rollback option for its existing routes; no automatic substitution after native failure was added, and the exact GPT-6.1 Sol requirement remains binding. Production default selection and the old transport were not modified or deleted during Stage23. The evidence now supports planning that migration without redesigning inference or adding relays/proxies.

Stage23 stops here. No additional trials, Stage24, OML, cheaper routing, Windows sandbox weakening or credential changes were initiated.
