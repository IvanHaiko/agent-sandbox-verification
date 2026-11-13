"""Publish the final Controller assessment only after completed-workflow audit PASS."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
REL = 'docs/stage23-wsl-evidence/continuation-schema-fixed'


def load(path):
    return json.loads(path.read_text())


def save(directory, name, value):
    (directory / (name + '.json')).write_text(json.dumps(value, indent=2))


audit = load(OUT / 'integrity-audit.json')
assert audit['passed']
reviewer_summary = load(OUT.parent / 'continuation/reviewer/summary.json')
architect_summary = load(OUT / 'architect/summary.json')
full_summary = load(OUT / 'full/summary.json')
assert reviewer_summary['gate'] == architect_summary['gate'] == full_summary['gate'] == 'passed'
assert reviewer_summary['accepted'] == architect_summary['accepted'] == 2 and full_summary['accepted'] == 1
architect_trials = [load(OUT / 'architect' / ('architect-' + str(n)) / 'assessment.json') for n in [1, 2]]
full = load(OUT / 'full/full-1/assessment.json')
new_trials = architect_trials + [full]
reviewer_rows, architect_rows, full_rows = [], [], []
for trial in reviewer_summary['trials']:
    record = trial['roles'][-1]
    reviewer_rows.append(f"| {trial['trial_id']} | gpt-6.1-sol / medium | `{record['thread_id']}` | "
        f"{trial['review']['recommendation']} | {len(trial['review']['blockers'])} / {len(trial['review']['findings'])} | "
        f"{trial['case_count']} / {trial['case_count']} | accept | {record['elapsed_seconds']:.3f} |")
for trial in new_trials:
    directory = OUT / ('full' if trial['trial_id'].startswith('full') else 'architect') / trial['trial_id']
    record = trial['roles'][0]
    proposal = load(directory / 'architect-result.json')
    normalization = load(directory / 'contract-normalization.json')
    save(directory, 'architect-marginal-value', {
        'authority': 'Controller', 'native_session': record['thread_id'],
        'accepted_clarifications': len(normalization['accepted_clarification_indices']),
        'accepted_risks': len(normalization['accepted_risk_indices']),
        'contract_requirements_changed': False, 'new_requirements': 0,
        'contract_interaction_clarification': 'Useful compact synthesis of escape/quote/whitespace/lowercase/whole-input rules.',
        'duplication': 'Mostly restates existing explicit criteria; no new requirement or novel material risk established.',
        'quality_improvement_attributable_to_architect': 'Not established: no controlled comparison, all earlier minimal workflows also passed.',
        'incremental_native_executions': 1, 'latency_seconds': record['elapsed_seconds'],
        'internal_request_count_and_cost': 'Not measured', 'mandatory_architect_default_justified': False})
    if trial['trial_id'].startswith('architect'):
        architect_rows.append(f"| [{trial['trial_id']}]({REL}/architect/{trial['trial_id']}/assessment.json) | "
            f"`{record['thread_id']}` | {record['elapsed_seconds']:.3f} | "
            f"{len(proposal['clarifications'])} / {len(proposal['risks'])} | "
            f"{trial['case_count']} / {trial['case_count']} | accept | all 5 removed |")
for record in full['roles']:
    full_rows.append(f"| {record['role']} | gpt-6.1-sol / medium | `{record['thread_id']}` | "
                     f"{record['elapsed_seconds']:.3f} | 0 | completed |")
repair = load(OUT / 'schema-repair.json')
new_cases = audit['total_frozen_cases']
total_cases = 70 + 46 + new_cases
architect_mean = sum(t['roles'][0]['elapsed_seconds'] for t in architect_trials) / 2
summary = {'verdict': 'STAGE23_PASS_NATIVE_BACKEND',
    'gates': {'smoke': '3/3 PASS', 'minimal': '3/3 PASS', 'reviewer': '2/2 PASS',
              'architect': '2/2 PASS after native output-schema repair', 'full_chain': '1/1 PASS'},
    'preserved_successful_trials_not_reexecuted': True,
    'successful_native_role_executions_stage23': 27, 'failed_architect_launches_stage23': 3,
    'failed_launches_without_recoverable_error': 2,
    'confirmed_repaired_failure': repair['native_error'],
    'model': 'gpt-6.1-sol', 'continuation_effort': 'medium',
    'new_frozen_cases_passed': new_cases, 'all_frozen_cases_passed': total_cases,
    'new_successful_native_contexts': 12, 'new_successful_workflow_repositories_removed': 15,
    'all_stage23_wsl_repositories_removed': 38,
    'fresh_contexts_blindness_freeze_readonly_roles_verified': True,
    'integrity_audit_passed': True, 'full_test_suite_run_during_latest_debugging': False,
    'targeted_architect_guard_passed': True,
    'production_defaults_changed': False, 'custom_transport_changed': False,
    'windows_sandbox_changed': False, 'stage24_started': False}
save(OUT, 'final-summary', summary)
save(OUT, 'targeted-guard-check', {'test': 'test_architect_cannot_change_original_acceptance_or_scope',
    'passed': True, 'runs': 2, 'scope': 'Only this guard; second run added reordered/duplicated criteria assertions.',
    'full_suite_run': False, 'native_inference_requests': 0})
report = f'''# Stage23 — Native Codex Execution Backend Assessment

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

One focused schema guard checks changed scope/criteria plus reordered/duplicated criteria. The latest debugging phase ran only that guard, rather than the full suite. Hash/receipt audits read completed artifacts without executing tests or inference. New evidence resides in `{REL}/`; prior `continuation`, `continuation-retry-1` and `continuation-diagnostic` archives remain intact. Architect-1's completed workflow is preserved with its own original source snapshots. Existing production transport/routing, Windows sandbox and authentication configuration were not changed. The project root is not a Git repository; no commit/PR is claimed.

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

[Schema repair receipt]({REL}/schema-repair.json) preserves the exact rejection, schema hashes and successful corrected Architect. Earlier diagnostic-loss handling was repaired; native error receipts now retain message/type/code/param without arbitrary stdout, reasoning or authentication data. The latest debugging phase ran one focused guard (expanded on its second run), with no full suite or repeated accepted smoke/minimal/Reviewer trials. Historical nine-test evidence is separate. A known setup correction succeeded; arbitrary runtime-error recovery is still not demonstrated.

## K. Isolation and cleanup

Every live role uses a fresh WSL repository and ephemeral native context. No resume, fork, shared conversation history, inherited API credentials or app pipe is used. Authentication remains native-owned outside role inputs. Native permissions retain minimal runtime reads and the installed release directory, bounded role workspace reads, `src` writes for Implementer, `tests` writes for Tester, no writes for Architect/Reviewer, project network disabled and `/tmp`/`TMPDIR` denied. No `:root` grant, full-access mode, sandbox bypass or Windows permission expansion was added.

Native preflights and exact complete repository comparisons include Git metadata and reject linked entries. Tester has no candidate/stub/handoff before freeze; the candidate reaches a separate Controller acceptance repository only after Tester shutdown. Frozen task/design/harness and candidate hashes stay unchanged. Architect/Reviewer repositories remain read-only; Controller owns their output archives. All 38 WSL repositories created across Stage23 gates and attempts are independently verified absent; Stage23B is separate. This checks the bounded repository/workflow scope, not every native-runtime write on the host.

[Final integrity audit]({REL}/integrity-audit.json) verifies all 12 resumed contexts, 15 completed-workflow repositories, all 38 historical/current repository absences, canonical equality, freeze ordering, candidate/test hashes, independently consistent frozen expectations and original source snapshots. It executes no model or tests.

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
{chr(10).join(reviewer_rows)}

Both read-only reviewers provided limited static rule-interaction corroboration. **Zero novel material findings, zero changed decisions.** Mean extra Reviewer latency was 16.686 seconds and one native role execution per workflow. Internal request/cost counts are unknown. Later three Reviewers likewise added no blockers/findings. No planted defects were used, so defect-detection sensitivity is not measured. [Original Reviewer summary](docs/stage23-wsl-evidence/continuation/reviewer/summary.json).

## P. Architect gate

**PASS 2/2 after bounded schema repair.** Each completed workflow used fresh native contexts for Architect, Implementer, blind Tester and Reviewer, with Controller-owned canonical contract, handoff, acceptance and final decision.

| Trial | Architect session | Architect seconds | Clarifications / risks | Frozen cases | Controller | Cleanup |
|---|---|---:|---:|---:|---|---|
{chr(10).join(architect_rows)}

All roles used `gpt-6.1-sol / medium`. Architect saw only the original task plus its output schema/instructions. Controller reviewed each clarification/risk, preserved every original criterion/constraint/interface/scope field and selected no code or algorithm recipe. No proposed requirement broadened the contract.

Architect-1 summarized escape/quote precedence, whitespace provenance, lowercasing protected letters, final-string emptiness/deduplication and whole-input errors. Architect-2 also made explicit that removed empty quote delimiters do not themselves break ordinary-whitespace runs. These are useful compact interpretations of existing rules, **mostly duplication of an already explicit contract**. Risks were in scope but no novel material risk was established. Both implementation/test portions passed (23 and 22 cases); earlier minimal workflows already passed, so improved quality cannot be attributed to Architect. Mean Architect gate overhead: **{architect_mean:.3f} seconds**, plus one extra native role execution per workflow. This sample does not justify mandatory Architect use for every task.

Failed launch history is retained: initial Architect-1 and its explicit retry lost diagnostic text; later Architect-2 failed with the exact array-constant schema rejection. That confirmed harness/configuration error justified the narrow repair/retry. Architect-1's accepted workflow was copied as evidence with its executed-source snapshots and was not run again. Architect-2 and the full chain use the corrected schema. [Final Architect summary]({REL}/architect/summary.json), [repair]({REL}/schema-repair.json), and per-trial normalization/marginal-value receipts record this distinction.

## Q. Full-chain trial

**PASS 1/1.** Fresh Architect → Controller-normalized contract → fresh Implementer → Controller handoff → fresh blind Tester → freeze → Controller deterministic acceptance → fresh read-only Reviewer → Controller decision → cleanup. All original criteria remain unchanged. No planted defect, Data Auditor, extra narration session or prior conversation was used.

| Role | Route | Native session | Seconds | Exit | Result |
|---|---|---|---:|---:|---|
{chr(10).join(full_rows)}

Frozen cases: **{full['case_count']}/{full['case_count']} PASS**; interface/properties/scope/hash checks passed. Reviewer recommended accept without blockers/findings; Controller accepted after cleanup. Candidate SHA-256 `{full['candidate_sha256']}`. Frozen design SHA-256 `{full['frozen_tester_sha256']}`. All five repositories were removed. [Full assessment]({REL}/full/full-1/assessment.json) and [Controller decision]({REL}/full/full-1/controller-decision.json).

## R. Final Stage23 verdict

**`STAGE23_PASS_NATIVE_BACKEND`.**

| Required gate / invariant | Evidence |
|---|---|
| Smoke | 3/3 PASS, preserved |
| Implementer → blind Tester | 3/3 PASS, preserved; 70 frozen cases |
| Reviewer | 2/2 PASS; 46 frozen cases |
| Architect | 2/2 completed workflows PASS; 45 frozen cases; setup failures disclosed |
| Fresh representative full chain | 1/1 PASS; {full['case_count']} frozen cases |
| Exact model and fresh native contexts | gpt-6.1-sol / medium for all workflow roles |
| Tester blindness/freeze, read-only Reviewer, Controller canonical state | independently audited |
| Artifact/hash recovery and cleanup | passed; all 38 Stage23 WSL repositories absent |
| Custom transport required | no |

Across accepted workflows **{total_cases}/{total_cases} frozen cases passed**. The final native gate succeeds after a documented schema compatibility correction; failed attempts are not erased or counted as successes. [Final Controller summary]({REL}/final-summary.json). This is the bounded Stage23 conclusion, not a statistical production reliability estimate.

## S. Recommended production role structure

For small bounded tasks, prefer **Implementer → independent Tester**, with Controller handoff/freeze/acceptance/decision/cleanup. For medium tasks, use that simpler sequence provisionally and add Architect when contract interactions or uncertainty warrant clarification; add Reviewer when independent static review has a concrete purpose. The four-role chain is now operationally validated, but this task does not establish that it should be mandatory: Architect largely restated explicit rules and Reviewer made no novel finding or changed decision. Medium-task complexity itself was not independently sampled. Keep the exact observed model route until a separately authorized routing study.

## T. Backend recommendation

**Native WSL Codex should become the preferred backend for the validated native workflow.** Retain the old custom transport intact as a legacy fallback/rollback option for its existing routes; no automatic substitution after native failure was added, and the exact GPT-6.1 Sol requirement remains binding. Production default selection and the old transport were not modified or deleted during Stage23. The evidence now supports planning that migration without redesigning inference or adding relays/proxies.

Stage23 stops here. No additional trials, Stage24, OML, cheaper routing, Windows sandbox weakening or credential changes were initiated.
'''
(ROOT / 'STAGE23_NATIVE_CODEX_BACKEND_ASSESSMENT.md').write_text(report, encoding='utf-8')
print(json.dumps({'verdict': summary['verdict'], 'gates': summary['gates'],
                  'new_cases': new_cases, 'total_cases': total_cases, 'full_cases': full['case_count']}, indent=2))
