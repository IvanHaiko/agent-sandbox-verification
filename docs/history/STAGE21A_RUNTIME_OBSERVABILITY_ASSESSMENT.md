# Stage21A — Runtime Observability Assessment

Date: 2026-10-06 (Europe/Berlin).

## A. Result

- **PASS**
- **accepted: true** — the Stage21A infrastructure patch meets its focused success criteria.
- Preserved implementation candidates remain **accepted: false**. No incomplete role was accepted or continued into testing/review.
- No Stage21 retry, Stage22, live role workflow, routing benchmark, or live Data Auditor invocation occurred.

## B. Original problem

Stage21 failed after the Implementer wrote its implementation and passed self-checks. The generic `Codex/model protocol denied` error discarded the causal layer. Candidate archival depended on completed role handoff, so disposable cleanup destroyed the implementation bytes. Complete upstream response evidence did not establish the downstream failure cause; it did not establish a socket timeout either.

## C. Changes

Exactly five production files changed:

1. `agent_system/runtime_observability.py` (new): fixed-category, sanitized failure classification; compact Controller receipts; scoped exact-byte candidate archives with SHA-256 and explicit unaccepted status. Default archive root is `runtime_root.parent/diagnostics/runtime_root.name/task_id/invocation_id`, outside the disposable runtime subtree.
2. `agent_system/model_tool_boundary.py`: track admitted successful writes and completed tool calls; retain tool validation/execution and relay request/response/transport failure layers. Relay exceptions export fixed details instead of arbitrary exception prose. No tool inventory, capability, route, admission, retry, network or timeout changes.
3. `agent_system/codex_tool_session.py`: preserve failures at startup/context exit; classify protocol-handler failures; record parser, handoff, last-phase, tool-result and byte counters. Snapshot before callers can delete role storage. Malformed final JSON uses the existing sanitized handoff-schema denial.
4. `agent_system/runners/chatgpt_plan.py`: copy the safe failure receipt into invocation evidence; capture an outer relay-shutdown failure after handoff; delete the owned model home after failure/candidate receipts are durable. Result acceptance semantics remain unchanged.
5. `agent_system/runners/tool_docker.py`: include the new observation module in the existing source binding hash. Existing source-bound admissions remain fail-closed; this stage does not silently refresh or issue production admission.

Validation additions: `tests/test_runtime_observability.py` and `validation/stage21a_observability.py`. Source-hash evidence confirms `.agent_system`, all original Stage21 drivers, their task/routing/timeouts, and other production sources are unchanged: [source scope](docs/stage21a-evidence/source-scope.json).

## D. Failure receipt

Actual native-Codex/synthetic-provider receipt:

```json
{
  "schema_version": 1,
  "invocation_id": "synthetic-failure-after-write",
  "role": "implementer",
  "model": "gpt-6-luna",
  "reasoning": "low",
  "role_status": "failed",
  "accepted": false,
  "recorded_at": "2026-10-06T16:28:29.558672+00:00",
  "failure_category": "handoff_schema_failure",
  "failure_detail": "Structured Codex role result schema mismatch",
  "request_count": 3,
  "tool_call_count": 2,
  "completed_tool_call_count": 2,
  "tool_result_returned": true,
  "last_completed_phase": "turn_completed",
  "response_validation_passed": true,
  "eof_observed": null,
  "reader_shutdown_confirmed": null,
  "socket_idle_timeout_observed": false,
  "parser_status": "passed",
  "handoff_status": "failed",
  "protocol_bytes": 13784,
  "stderr_bytes": 0,
  "protocol_anomaly_counters": {},
  "candidate_written": true,
  "candidate_preserved": true,
  "candidate_archived": true,
  "candidate_skipped_count": 0,
  "candidates": [
    {
      "path": "src/utility.py",
      "sha256": "0b97c8dee8923810d0489ef3b21b88bf27e3636b2c0010f4e10d3c65272c8c70",
      "archive_path": "candidates/src/utility.py",
      "originating_invocation_id": "synthetic-failure-after-write",
      "archived_at": "2026-10-06T16:28:29.558482+00:00",
      "status": "unaccepted_diagnostic_candidate",
      "accepted": false
    }
  ]
}
```

Full receipt: [failure_receipt.json](docs/stage21a-evidence/diagnostic/failure_receipt.json).

Details come from fixed local literals and known boundaries, never raw exception/provider text. No tokens, cookies, authorization headers, environment dump, raw stream, model-home contents or credential-bearing stderr are included. Synthetic credential canaries in errors/candidates are suppressed; secret-bearing candidates are skipped. `null` transport fields mean unavailable: this integration used a local synthetic provider, not `PlanUpstream` HTTP transport. Separate local tests prove preservation of existing EOF/shutdown booleans and explicit socket-timeout evidence.

## E. Candidate preservation

The integration executed one fixed Docker write, then one fixed Docker self-check. Both returned 0. The third synthetic response completed normally, but final role JSON failed the required schema. The native role remained failed.

- Original candidate: `C:\Users\4ivan\codex-multi-agent\.test-tmp\stage21a-offline\runtime\codex-agent-system-5afe42350c3960a7\worktrees\STAGE21A\implementer\src\utility.py`
- Relative task path: `src/utility.py`
- SHA-256: `0b97c8dee8923810d0489ef3b21b88bf27e3636b2c0010f4e10d3c65272c8c70`
- Exported diagnostic copy: `docs/stage21a-evidence/diagnostic/candidates/src/utility.py`
- Originating invocation: `synthetic-failure-after-write`
- Role failure: `handoff_schema_failure`
- Candidate status: `unaccepted_diagnostic_candidate`; **accepted: false**.
- Cleanup: both tool containers and their checkout/transfer storage removed; model home, role checkout, whole disposable runtime and validation project removed. Exact candidate bytes survived runtime removal and are retained in the exported archive.

Ordering: detect failure → collect safe evidence → inspect only successful-write paths against existing scope/role rules → archive/hash candidate → persist receipt → return control for disposable storage removal. Candidate preservation never commits/integrates the candidate or creates a completed-role handoff.

## F. Validation

### Deterministic/local tests

- Initial boundary regression: **144 passed**.
- Expanded regression: **267 passed**, covering boundary reconciliation, Docker policy, hardened workflow, isolation and response-error sanitization. [JUnit](docs/stage21a-evidence/regression.xml)
- Final-source focused/boundary check: **167 passed**, including **23 Stage21A tests**. [JUnit](docs/stage21a-evidence/final-check.xml)

| Scenario | Result |
| --- | --- |
| A: failure before any write | PASS — protocol category retained, candidate_preserved=false, cleanup succeeds |
| B: successful write/self-check then failed handoff | PASS — exact bytes/hash archived, role failed, candidate unaccepted, storage removed afterward |
| C: completed normal role | PASS — successful handoff and ordinary candidate handling remain; no failure archive on normal success |
| D: out-of-scope file | PASS — forbidden/private/out-of-scope and independent-test paths are not archived |
| E: cleanup | PASS — evidence survives; model/role storage removed; Docker disposal confirmed; credentials unchanged |
| Explicit synthetic socket timeout | PASS — socket_idle_timeout, without raw logs |
| Response and final schema failures | PASS — response_validation_failure and handoff_schema_failure remain distinct |
| Tool validation/execution failures | PASS — distinct categories and completed-call counts; exception prose suppressed |
| Finalization and shutdown failures | PASS — handoff_finalization_failure / relay_or_session_failure |
| Unknown/generic denial with completed upstream evidence | PASS — unknown_runtime_failure; no inferred socket timeout |
| Incomplete Implementer continuation | PASS — Controller remains FAILED, no completed implementation evidence or integration/downstream continuation |
| Secret-bearing/hardlinked candidate | PASS — skipped; no arbitrary/private file archive |
| Existing harmless anomalies | PASS — recorded counters remain; no inferred causation or handling redesign |

### Synthetic provider integration

Two offline validation executions, each using the pinned native Codex app-server, a deterministic localhost Responses provider, and **two real Docker tool actions** (write/check). Each used **3 synthetic requests**; **6 total synthetic requests**, **4 total Docker actions**. Both reproduced failure after candidate work and cleanup survival. [Final integration](docs/stage21a-evidence/offline-integration.json), [first integration](docs/stage21a-evidence/offline-integration-first.json).

Docker actions used the existing private pre-admission bootstrap used by local isolation probes, with a fixed validation-only adapter and host-process trap. No production admission or live authorization was issued. Production admission checks are unchanged. The native integration ran before the final small shutdown-literal/runner-fallback addition; the final local suite verifies that addition. Integration source hashes are retained for reproducibility.

### Real model calls

**0.** Synthetic/local checks established the required properties; no inference request was sent to an upstream model service.

## G. Model usage and cost discipline

- Models actually used for inference: **none**.
- Declared synthetic Codex route: `gpt-6-luna`, reasoning `low`; responses were authored locally.
- Live model request count: **0**.
- **Astra calls = 0**, at every reasoning level.
- Sol High calls = **0**; no fallback or model-routing benchmark.
- Production role model strategy/routing remains untouched.

## H. Security/containment regression

- Production edits limited to the five files in section C; source comparison confirms all other existing files unchanged.
- No credential exposure. Before/after SHA-256 comparisons match for all three credential-store files; no credential values were exported. [Integrity receipt](docs/stage21a-evidence/credential-integrity.json)
- No generic model host-read capability added. Candidate inspection is Controller-owned and limited to successful writes rechecked against existing mutation/role scopes.
- Scope/protected-path enforcement, role network `none`, checkout isolation, credential ownership, Controller/role separation, independent Tester design, action admission and security architecture retained.
- **Stale owned containers = 0**, confirmed by per-run ownership checks and the final Docker listing.
- Model homes and disposable role checkouts/runtime removed; all six Stage21A pytest storage roots removed. [Storage cleanup](docs/stage21a-evidence/test-storage-cleanup.json)
- Host fallback unchanged: model-selected writes/checks execute inside Docker. The offline integration's host-process trap passed.

## I. Root-cause knowledge

### What Stage21A now makes observable

Known transport/socket-timeout, response validation, tool request/execution, native protocol, role schema/finalization, relay/session and Controller rejection boundaries retain safe classifications. Receipts preserve available validation/EOF/reader status, request/tool counts, last completed phase, parser/handoff state, protocol byte/anomaly counters and candidate identity/acceptance status.

### What remains unknown

The historical second Stage21 denial's precise cause is still unknown. Its candidate cannot be reconstructed from missing bytes. Stage21A establishes a reproducible synthetic failure and future evidence retention; it does not prove that the historical failure was a socket idle timeout or was caused by any harmless anomaly. Native parser failure can remain a broad protocol category when existing runtime evidence cannot distinguish malformed/partial/overflowing frames. Unclassified failures explicitly remain unknown.

## J. Readiness for Stage21 retry

- **Can a third attempt fail without losing an allowed written candidate? Yes**, when an admitted successful write produced a permitted regular file that the Controller can safely read and archive. The default archive survives deletion of `runtime_root`; archive/receipt location is explicitly diagnostic and unaccepted.
- **Will generic denial retain materially better safe classification? Yes**, known failure boundaries and supporting counters survive; unsupported precision remains unknown.
- **Did Stage21A alter the frozen task, production routing, timeouts or security architecture? No.** Existing source-bound admission must still validate the changed implementation before a future authorized live run; it was not bypassed/refreshed here.

Stage21A stops here. **Stage21 was not rerun.**
