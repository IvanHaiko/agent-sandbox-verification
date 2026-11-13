# Stage20 — First real multi-agent workflow

**PASS_MULTI_AGENT_WORKFLOW — accepted: true.**

## Exact frozen task

Implement `src/slugify.py` with `def slugify(value: str) -> str`. Lowercase ASCII letters; retain ASCII letters and digits. Trim whitespace and replace every whitespace run with one hyphen (including tabs/newlines). Remove ASCII punctuation except hyphen, including underscore; removal does not insert a separator. Collapse repeated hyphens and strip edge hyphens. Empty or whitespace-only strings return the empty string.

Standard library only; pure function; ordinary ASCII strings are the supported domain. Unicode and non-string inputs are unspecified. Punctuation removal does not introduce a separator: `a_b` becomes `ab`. Tabs/newlines count as whitespace. The Controller committed this task and a `NotImplementedError` baseline before any role ran.

## Actual routing and usage

Account catalog listed gpt-6-astra and gpt-5.6-sol. gpt-6-sol was absent; available Sol High explicitly disclosed before inference.

| Role | Actual route | Sessions | Model requests | Tool calls | Complete |
|---|---|---:|---:|---:|---|
| orchestrator | gpt-6-astra / medium | 1 | 1 | 0 | True |
| implementer | gpt-5.6-sol / high | 1 | 6 | 5 | True |
| test_engineer | gpt-5.6-sol / high | 2 | 3 | 1 | True |
| reviewer | gpt-6-astra / medium | 1 | 1 | 0 | True |

Total: 11 model requests, 6 model-selected Docker actions, 1 additional Controller Docker interface check. Tester design and execution used separate fresh sessions. No shared model history or monetary estimate. Returned numeric usage is recorded in the companion JSON; detailed per-session observations are in `docs/stage20-evidence/role-counts.json`. Seven focused driver checks passed, including one synthetic-provider real Codex/Docker roundtrip; those consumed zero live model calls.

## Explicit handoffs

**Architect → Implementer/Tester:** task ID, contract version 1, required signature, all five frozen acceptance criteria, sole allowed file `src/slugify.py`, constraints and five compact risks. The risks highlight underscore removal, whitespace coverage and cleanup order. [Contract](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/architect-result.json).

**Implementer → Controller/Reviewer:** completed; sole changed file `src/slugify.py`; single-pass implementation; 12 passing self-check cases and diff inspection. [Implementation result](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/implementer-result.json).

**Tester design → frozen cases:** 18 independently selected input/expected-output pairs plus idempotence, output shape and input unchanged. Cases include every ASCII punctuation character except hyphen, form feed/vertical tab, punctuation-created adjacent hyphens, and mixed whitespace/hyphen interactions. [Frozen design](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/test-design-result.json); [freeze receipt](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/test-freeze.json).

**Tester execution → Reviewer:** passed; one Docker acceptance action executed three unittest methods covering the 18 cases, interface and 54 property subchecks. No failures. [Execution handoff](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/test-execution-result.json).

**Reviewer → Controller:** accept. The supplied final diff preserves the required interface and satisfies every frozen acceptance criterion, including punctuation deletion without separators, mixed whitespace normalization, and hyphen collapse after punctuation removal. Changes are confined to src/slugify.py, with no dependencies or I/O. Independent acceptance evidence reports passing cases, interface, and property tests, supported by 12 passing implementer cases. No in-scope defects identified. [Review handoff](C:/Users/4ivan/codex-multi-agent/docs/stage20-evidence/reviewer-result.json).

## Tests and Controller acceptance

Implementer successful self-check case counts: [12]. Independent cases: 18; properties: ['idempotence', 'output_shape', 'input_unchanged']. Independent acceptance passed: True. The Controller generated a small unittest harness directly from the frozen Tester cases/property choices, then exposed the candidate. Tests and candidate hashes stayed unchanged during execution. Required public signature and self-check results were verified. Final acceptance required passing independent tests, valid structured role results, the exact allowed mutation scope, Reviewer acceptance and containment cleanup. No repair cycle was used.

```text
test_cases (tests.test_acceptance.Acceptance.test_cases) ... ok
test_interface (tests.test_acceptance.Acceptance.test_interface) ... ok
test_properties (tests.test_acceptance.Acceptance.test_properties) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.001s

OK
```

## Isolation and containment

Each invocation had a distinct execution identity, private ephemeral Codex home and fresh session. All four roles had separate isolated checkouts; Tester design and later execution shared only explicit frozen handoff artifacts. Tester design received exactly task and contract. The candidate was copied only after the design artifact was frozen. Reviewer received the compact evidence bundle and had no mutation action.

Model-selected project operations ran exclusively through the admitted Docker runner: network none, bounded resources, readonly tests/inspection, fixed writer path. Unknown selectors, wrong identity and readonly escalation were blocked before dispatch. A host-process trap allowed only the existing Controller Git/Docker/Codex/ACL/cleanup utilities. Credentials remained Controller-owned.

Inherited signed Stage19 proofs after verification of identical engine, image, configuration, containment code and Codex; rebound only to fresh project. New task actions verified with real Codex/Docker synthetic roundtrip.

Containment result: {"production_source_unchanged": true, "credential_store_unchanged": true, "stale_owned_containers": 0, "model_homes_removed": true, "role_network": "none", "host_fallback": false, "independent_context_before_candidate": true, "docker_cleanup_confirmed": true, "disposable_role_storage_removed": true}. All role/runtime storage was removed; the disposable repository and explicit evidence remain. Production `agent_system` Python source was unchanged.

## Observations and usefulness

1. Architect produced a useful compact contract: it clarified underscore removal, punctuation deletion versus separator insertion, and whitespace/order risks.
2. Implementer completed: True; only the permitted utility changed.
3. Tester independently designed 18 cases, including behavioral combinations, plus selected properties.
4. No missed implementation defect was caught in this run when the independent suite passed; broader coverage is evidence of usefulness, not proof of defect detection.
5. Reviewer checked contract/diff/evidence consistency and gave the recorded recommendation. It found no blocker in a passing run; its marginal value on this tiny utility is limited.
6. No forbidden context receipt was observed. Saved context manifests show exact handoff keys; complete conversations and hidden reasoning were never serialized as workflow state.
7. No model-selected action escaped its capability boundary.
8. Final artifact accepted: True, supported by the independent suite, interface check, scope and review. Unicode behavior remains outside this task.
9. Actual model/tool counts and available usage are above and in the JSON; there was no routing benchmark.
10. The second Tester session mainly reports a deterministic test result; each fresh Codex session repeats instruction/schema overhead. Two Implementer inspections repeated data already in its prompt. The input_unchanged property adds little for immutable Python strings. Architect and Reviewer added boundary clarification and confirmation but found no implementation defect.

Protocol anomalies: completed_function_omitted_from_final, nonexecutable_stream_final_mismatch, nonstandard_or_absent_mime. These were observed and continued without demonstrated project/security impact. No Stage19 MIME/SSE/OAuth/lifecycle implementation was changed. A pytest cache permission warning was non-blocking; all seven pre-run checks passed.

Controller disposal initially failed on 12 readonly copied Git object files after the project and review had passed. The provisional assessment incorrectly classified this as a capability failure despite zero violations; it is preserved in `assessment-before-storage-cleanup.json`. Controller-only cleanup repaired those 12 copied-file attributes and completed disposal without any model/role rerun. This was a storage-cleanup issue. `cleanup-recovery.json` records the correction, and `executed-driver.py` preserves the original executed driver. Readonly handling and correct failure classification were then added only to the Stage20 helper. Its cleanup regression check passed using an owned workspace temp directory after the first test setup encountered a shared-host-temp permission error.

## Final diff

```diff
diff --git a/src/slugify.py b/src/slugify.py
index 24d2036..92889e2 100644
--- a/src/slugify.py
+++ b/src/slugify.py
@@ -1,2 +1,17 @@
 def slugify(value: str) -> str:
-    raise NotImplementedError
+    """Return a lowercase, hyphen-separated slug for an ASCII string."""
+    slug: list[str] = []
+
+    for character in value:
+        if "A" <= character <= "Z":
+            slug.append(character.lower())
+        elif "a" <= character <= "z" or "0" <= character <= "9":
+            slug.append(character)
+        elif character == "-" or character.isspace():
+            if slug and slug[-1] != "-":
+                slug.append("-")
+
+    if slug and slug[-1] == "-":
+        slug.pop()
+
+    return "".join(slug)```

Disposable project: `C:\Users\4ivan\codex-multi-agent\.test-tmp\stage20-workflow\project`. Accepted commit: `7bba581c95cc4796215641bf6f59a3e34076c365`.

## Stage21 recommendation

Review this evidence first. Consider a single bounded task with a less obvious behavioral defect, retain independent test freezing, and let Controller execute frozen tests without a second Tester narration session. Do not benchmark or redesign transport based on this run.

Stopped after this workflow and assessment. No OML, Data Auditor, benchmark, routing optimization, repeated experiment or generic action platform was started.
