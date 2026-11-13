# Stage 28 — Multi-Agent Architecture Benchmark II

## 1. Executive summary

**Architectural decision: INCONCLUSIVE.** Both architectures delivered focused IGDB reliability implementations that passed **56/56 frozen external cases**, **168/168 unchanged project regressions**, and real PostgreSQL checks. Both independently designed suites detected **all three predetermined behavioral mutations**. Both final Reviewers accepted the code. These results do not demonstrate an engineering-quality advantage that earns the custom framework's additional complexity.

The experiment also demonstrated useful review and isolation differences. A's Reviewer found a genuine shared-mapping replay defect. B's Reviewer found a compatibility regression introduced while trying to satisfy a defective independent assertion. Both defects were repaired. B enforced tested role filesystem restrictions and Reviewer write denial; A's configured Reviewer could open its source for writing, although hashes prove it did not change it.

Neither independent suite was entirely valid: A retained two erroneous tests and B one. B's original workflow also remained rejected because the **Stage 28 adapter incorrectly applied fixed-target change validation to transformer-only repairs**. This is a new coordinator adapter defect, not Stage 27's cleanup defect and not evidence that the existing framework malfunctioned. Review evidence detail remained asymmetric. Consequently, this run supplies stronger behavioral and isolation evidence, but still cannot establish a reliable complete-architecture efficiency or reliability winner.

Executed on **9 October 2026**. No candidate patch was applied to the original Steam ETL checkout. No active architecture was modified and Stage 29 was not started.

| Measure | A — native Codex | B — existing custom framework |
|---|---|---|
| Final held-out acceptance | **56/56 passed** | **56/56 passed** |
| Unchanged project regressions | **168/168 passed** | **168/168 passed** |
| Full project + candidate + external run | 281 passed, zero failures/errors/skips | 303 passed, zero failures/errors/skips |
| Frozen independent suite | 67 passed, **2 test defects**; zero errors/skips | 74 passed, **1 test defect**; zero errors/skips |
| Distinct mutation defects detected | **3/3**, excluding existing failing tests | **3/3**, excluding existing failing tests |
| Final code review | Accept, no blockers | Accept, no blockers |
| Candidate repair feedback cycles | 1, genuine replay defect | 2: erroneous test feedback, then genuine induced regression |
| Normal workflow result | Completed with frozen harness errors; no clean independent acceptance | Original Controller rejects; repair artifact admission fails; no clean independent acceptance |
| Recorded workflow window | 911.014 s | 912.961 s |
| Model sessions | 4: parent plus three reused subagents | 6 ephemeral role sessions, including repairs/review follow-up |
| Reviewer write denial | **Not enforced** on two actual probes; no bytes changed | **Enforced** on actual probes and launcher preflights |
| Human interventions | 0 | 0 |

Passing case counts are engineering evidence, not declarations that the failed independent gates or B Controller decision passed. The same corrected external suite was sealed before either candidate existed.

## 2. Exact task and rationale

The task is **reliable IGDB bronze-file replay**, selected from the actual committed Steam ETL source. Baseline commit: **`0653617666399590c853c39f08e8cf97c9eca45c`**.

`transform_igdb_search_results` uses `raw_data.get("data", [])`, silently interpreting a missing response body as a valid empty search. Record and nested-field validation is inconsistent. The IGDB game and Twitch mapping upserts unconditionally rewrite `updated_at`, so retrying an identical saved file changes persisted values. The existing file loader already has a transaction boundary; preserving and proving that boundary is part of this task, rather than claiming a pre-existing partial-commit defect.

The [frozen contract](docs/stage28-verification/task-contract.md) specifies explicit envelope validation, valid integer IDs/names, duplicate-ID rejection, optional nested collection rules, validation before connection acquisition, empty-batch behavior, file-wide atomicity, saved-file retry, NULL-safe timestamp-preserving replay, updates/remapping, and committed compatibility. Modification scope is exactly **`src/transform.py`, `src/load.py`, and new `tests/test_igdb_reliability.py`**. Existing tests, schema, migrations, dependencies and unrelated behavior are immutable. The task interacts with transformation, three persistence helpers, file transaction ownership and public dispatch; it is not an isolated utility.

This excludes Stage 25's atomic Twitch-hour replacement, Stage 26's Steam Store outcome refactor and Stage 27's SQL splitter. The original source archive excludes the checkout's uncommitted work, ignored production data and credentials.

## 3. Methodology and freeze

Stage 25–27 assessments, active framework source/configuration, Stage 27 experiment/closeout, verification receipts and delivery ZIP were inspected first. The Stage 27 ZIP matched its recorded SHA-256 and passed all 137 member CRC checks. [Previous delivery verification](docs/stage28-verification/previous-delivery-verification.json), [methodology](docs/stage28-verification/methodology.md).

The [freeze receipt](docs/stage28-verification/freeze.json) fixes the commit, task, allowed scope, rubric, external suite, adapter, dependencies, **gpt-6.1-sol / medium**, order **A then B**, three mutations and maximum **two candidate repair cycles**. No post-exposure requirement or assertion was changed. Repair feedback comes from frozen independent tests or concrete review findings; held-out evaluation is final and cannot tune candidate tests.

The coordinator authored the held-out suite independently before either implementation. The initial suite had a missing closing list bracket and failed baseline collection. Those original frozen bytes, original freeze and failed result remain preserved. Before candidate exposure, only the bracket was corrected, baseline checks rerun and the corrected hash sealed. The corrected baseline produced **2 passes and 54 failures, zero errors/skips**, demonstrating selected weaknesses rather than 54 distinct bugs. [Correction receipt](docs/stage28-verification/evaluator-correction.json). This pre-exposure defect limits confidence in preparation quality; it did not expose either candidate to the evaluator or change assertions in response to candidate behavior.

Runtime observations: Linux Codex **0.160.1**, Python **3.14.4**, PostgreSQL **18.6**, exact committed requirements, including psycopg **3.3.4**, pytest **9.0.3** and Ruff **0.15.12**. [Versions](docs/stage28-verification/runtime-versions.json), [dependencies](docs/stage28-verification/installed-dependencies.txt), [CLI help](docs/stage28-verification/native-exec-help.txt), [features](docs/stage28-verification/native-features.txt). Current [official Subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents) was fetched separately; installed probes determine demonstrated guarantees, rather than assuming newer documentation describes every older-runtime behavior.

## 4. Configuration differences

A used one native CLI Orchestrator and exactly three native subagents: blind Tester, Implementer, Reviewer. Fresh contexts and the common model/effort were requested and recorded by its parent. The Tester ran first and froze its files before implementation. The original Implementer and Reviewer were reused for repair and reassessment. Native delegation, waits, artifacts and review were controlled by the native Orchestrator.

B used the unchanged native launcher, selected role bundles, private repositories, snapshot/scope checks, structural test validation, design freeze, deterministic acceptance and read-only semantic review. A deterministic coordinator replaces A's model Orchestrator. Its Implementer ran first and its workspace was removed before blind testing. Repair/review invocations used fresh ephemeral sessions, as that architecture normally does. No Architect or new role type was added.

Both Testers received the same contract, public interface names, unchanged schema/fixtures and design schema, with no candidate, diff, implementation handoff, reasoning or held-out evaluator. The blind suites were never edited after completion. Both configurations used the **existing `RoleTestEnvironment` and disposable PostgreSQL provisioning**. That shared facility executes predefined checks; it does not choose native A's roles or code. This remains an orchestration/artifact comparison with shared custom test support, not proof that every custom runtime facility can be removed.

Both Reviewers received original/candidate source, patch, contract, rubric, frozen design/harness and own independent result. **Details were not fully equalized:** A's native parent additionally supplied development-check evidence and detailed failure output; B's adapter supplied aggregate independent counts and omitted development receipts/tracebacks. B's Reviewer explicitly identified that evidence gap. No successful Reviewer was resampled to improve its input. Comparative review superiority therefore cannot be inferred.

## 5. Functional and regression results

The same [external suite](docs/stage28-verification/test_external_acceptance.py) ran on separately reproduced final patches after both workflows stopped. Both passed all 56 cases without errors/skips. Checks include malformed input before connection acquisition, NULL nested data, input preservation, correct dispatch, NULL-safe/key-order-insensitive replay, changed values, unique remapping, no absence deletion, rollback of earlier updates and durable previous files followed by saved-file retry. Database cases used actual PostgreSQL and the original migration chain with `REQUIRE_DB_TESTS=1`.

The full A run passed **281 cases = 168 original + 57 candidate + 56 external**. B passed **303 = 168 original + 79 candidate + 56 external**. The original 168 cases were separately counted from JUnit by baseline module identity. Added test counts are not a quality ranking. All 39 existing public function argument signatures across the two modules were unchanged by AST comparison. Both clean patches reproduced archived candidate bytes against the pinned source. [Evaluation results](docs/stage28-verification/evaluation-summary.json), [compatibility audit](docs/stage28-verification/compatibility-audit.json).

## 6. Independent test quality

Both designs cover all seven declared categories, validate behavior without new private-helper assumptions, and include meaningful real-database rollback/retry and persisted-value replay checks. Failures are injected after real writes through established public seams; database snapshots establish rollback and earlier-file durability. Both test JSON key-order invariance, NULL behavior, timestamp changes and compatibility.

A supplied 12 top-level functions / 69 collected cases. Two are defective: a precedence assertion incorrectly discards a distinct external Steam ID, and dispatch calls `load_data(path)` although the established signature requires `load_data(source, file_path, ...)`. The final unchanged suite remains **67 passed, 2 failed**. B supplied 17 top-level functions / 75 cases, including useful raw-JSON-only metadata updates and store-URL updates preserving row identity. Its precedence assertion has the same distinct-ID mistake; final result **74 passed, 1 failed**. B's dispatch test correctly binds the public interface. [A frozen suite](docs/stage28-verification/A/frozen/test_independent.py), [B frozen suite](docs/stage28-verification/B/frozen-acceptance.py).

The common precedence error is material: websites replace external links with the **same `(store, store_game_id)`**, not all links from that store. Both blind designs inferred the broader rule despite the requirement to preserve committed semantics. A clearer public contract example could have reduced this risk; no clarification or test correction was introduced after exposure. Independent context alone does not ensure an accurate oracle. Both suites remain failed, rather than silently excluding their flawed cases from acceptance. No coverage percentage was measured.

## 7. Mutation effectiveness

Three task-specific suffix mutations were fixed in the original freeze and applied only to disposable evaluation copies. Each candidate's unmutated external suite passes; each mutant causes behavioral assertion failures with zero errors/skips, verifying a meaningful defect.

| Predetermined defect | A independent: **new** failing cases | B independent: **new** failing cases | External failures, each candidate |
|---|---:|---:|---:|
| Treat missing `data` as an empty result | 1 | 1 | 2 |
| Unconditionally rewrite game timestamp on replay | 4 | 5 | 3 |
| Commit each game before the rest of its file | 3 | 3 | 2 |

Each independent suite detected **three distinct defects**. Existing erroneous tests are excluded from detection credit by comparing failing JUnit node identities with the unmutated run. Raw independent failure totals were A **3/6/5**, B **2/6/4**, including their original two/one failures. Multiple failed assertions are not multiple bugs. No suite was improved after seeing mutations. [Incremental detection evidence](docs/stage28-verification/quality-analysis.json).

## 8. Code review and maintainability

A's initial Reviewer found a genuine defect: two games sharing a Twitch UID can transiently remap it during identical replay and advance its timestamp. One Implementer repair resolves final mapping owners before writes while preserving last-game precedence, and adds a real PostgreSQL collision regression. Final review accepts. A also suppresses unchanged store-link writes and superseded store mappings; these are reasonable scoped choices, not proof of superior engineering.

B's initial implementation already selected final Twitch mappings. Its first repair followed the faulty independent precedence expectation and incorrectly suppressed valid distinct external Steam links. The independent suite temporarily became **75/75 green while the code regressed**. B's Reviewer reproduced that compatibility defect against original/candidate transformers and requested restoration. The second repair restores committed semantics; final review accepts, while the frozen erroneous assertion fails again. This is useful demonstrated review value and a concrete warning against treating a passing independent suite as the only oracle.

Both final approaches are proportionate: explicit validation, existing transaction ownership, PostgreSQL `IS DISTINCT FROM` predicates and bounded mapping selection, without new dependencies, migrations or general abstractions. B leaves harmless store-link upserts unconditional, preserving row values/creation timestamps; the contract does not require eliminating every physical write. No final blocking defect was established on the frozen criteria. [A final review](docs/stage28-verification/A/results/reviewer-result.json), [B initial review](docs/stage28-verification/B/reviewer0-result.json), [B final review](docs/stage28-verification/B/reviewer1-result.json).

## 9. Operational efficiency

Recorded A workflow window: **911.014 s (15 min 11.014 s)**. B: **912.961 s (15 min 12.961 s)**. These are observed execution windows, **not time-to-success**: neither independent gate passed, and B's original Controller rejected the run. Common provisioning/baseline checks took **137.100 s**; final common evaluation subprocess windows totaled **68.281 s for A**, **65.693 s for B**, excluding copy/cleanup overhead.

A's parent-reported child execution intervals total approximately **799.579 s**: Tester 214.330; initial Implementer 205.385; repair 122.246; initial Reviewer 123.310; reassessment 134.308. B's launcher-measured six process intervals total **870.589 s**. A's parent session is already included in its workflow window and must not be added again. These session intervals include tools and checks; **pure model inference duration is not exposed**.

Residual workflow time is about **111.435 s for A** and **42.372 s for B**, but includes independent evaluation, artifact operations, native dispatch/preflight and setup; it is not a clean orchestration-overhead measurement. A's role intervals are parent-reported, B's launcher-measured. A's prebuilt role repositories precede its CLI window, while B provisions role repositories within its window. Thus even the nearly equal wall times do not establish equal total operating cost. The supported common elapsed window begins at provisioning and ends at delivery seal; preliminary brief/source inspection and suite authoring were not timestamped, so a complete first-read-to-delivery time cannot honestly be reconstructed. [Metrics and boundaries](docs/stage28-verification/metrics.json).

## 10. Model usage and accounting limits

A's native turn JSON reports **916,651 input**, **876,672 cached input**, **10,314 output**, and **596 reasoning-output tokens**. Independent child counters and aggregation scope are unverified. B's six native text counters are **57,349; 48,255; 36,176; 39,836; 68,014; 41,861**, totaling **291,491 reported units**, without input/cache/output breakdown.

These are incompatible accounting boundaries and cannot support a token-efficiency ratio or precise dollar estimate. No custom accounting subsystem or framework instrumentation was added. Corresponding engineering roles used the same requested model/effort; B has per-session resolved-model receipts, while A's child settings/fresh-context choices are parent-reported. Provider request counts and internal transport retries are unavailable.

## 11. Practical isolation evidence

| Property | A | B |
|---|---|---|
| Context separation | Fresh native role contexts requested/reported; child trace detail limited | Fresh ephemeral CLI sessions, no inherited conversation, recorded by launcher |
| Filesystem separation | Separate Git copies; recorded parent profile can read/write peer role trees | Private role repositories and bounded native permissions; selected forbidden-path preflights pass |
| Blind design | Tester freeze precedes Implementer start; final frozen bytes match | Implementer repository removed before Tester; public-only bundle and denied selected paths; bytes match freeze |
| Reviewer read-only | Requested configuration; actual O_WRONLY probe **succeeds** twice | Actual probe **denied with errno 30**; native preflight/snapshot confirms read-only inputs |
| Artifact integrity | Frozen hashes and before/after review hashes match; clean patch reproduced | Snapshots, frozen hashes, read-only review and clean patch reproduction pass |
| Cross-configuration exclusion | Recorded parent profile denies existing B candidate, held-out suite and original source | Selected A candidate/original/held-out paths denied during Tester preflight; other roles bounded to their own roots |

A's [targeted parent probe](docs/stage28-verification/A/permission-probe.json) verifies all target paths existed outside the sandbox; denied paths appear absent inside it. It does not claim unobserved per-child filesystem policies. Reviewer probes only opened descriptors and wrote no bytes. Both candidates and review inputs remained unchanged by review. Native contexts and directory layout are not equivalent to enforced filesystem separation. B demonstrates stronger restrictions on the tested paths, not a general host-security certification or automatic engineering advantage. No cross-configuration contamination was observed; missing child traces are missing evidence, not proof of a violation.

## 12. Failures, recoveries and interventions

| Event | Actual source | Recovery / preserved outcome |
|---|---|---|
| Held-out suite missing bracket | Shared evaluator / coordinator | Corrected and resealed before candidates; original suite/freeze/collection failure retained |
| A initial shared-UID replay defect | Candidate code | One genuine repair; final review accepts |
| A two independent assertions | Agent decision, Tester oracle | Remain frozen and failing; never counted as two candidate bugs |
| B erroneous independent precedence assertion | Agent decision, Tester oracle | Remains frozen and failing in final code |
| B repair introduces store-wide suppression | Candidate code / Implementer decision following faulty feedback | Reviewer finds actual compatibility loss; second repair restores behavior |
| B two repair invocations rejected despite authorized changes and native exit 0 | **Stage 28 benchmark adapter** | Fixed target `src/load.py` did not change on transformer-only repairs. Original failed receipts/decision retained; no validator bypass or successful-run relabeling |
| A scope assertion includes handoff metadata; result overwrite patch rejected | Native Orchestrator artifact operations | Corrected checks/copy within same run; no candidate/test changes |
| A Reviewer write opens succeed | Native role configuration / enforcement setup | Recorded twice; no writes; guarantee remains unestablished |

B's adapter reused the launcher's single-target delta admission with `target='src/load.py'` for every repair. Both rejected repairs changed only authorized transformer/test/handoff files. The selected target was unchanged, so validation stopped before examining their artifacts. The final source nevertheless passes held-out/regression checks. A zero-model-call [diagnostic](docs/stage28-verification/quality-analysis.json) verifies the archived full candidate syntax/handoff and authorized changes; it **does not overwrite** original invocation status or [Controller rejection](docs/stage28-verification/B/controller-decision.json). This is not a recurrence of the Stage 27 cleanup bug; its owned-scratch correction worked throughout Stage 28.

Development check failures are retained: A one failed unit invocation; B two initial failed unit/integration invocations and one failed first-repair unit invocation. These are within-session development, separate from post-handoff repair cycles. All final development checks pass. Native model processes reported no provider failure or timeout; B shutdown confirmations pass. Initial host sandbox restrictions on WSL/original Git inspection were resolved through the authorized execution route before roles. No successful role was resampled for quality, and no model/dependency substitution occurred.

**Human interventions: zero. Coordinator corrective intervention: one pre-exposure evaluator syntax correction. Post-exposure coordinator candidate/test edits: zero.** The later B validation diagnostic is analysis only, without new model calls or a corrective rerun. Unrecovered outcomes are the frozen test defects, B's original artifact-admission failure and A's unenforced Reviewer write restriction.

## 13. Limitations

One trial per configuration, fixed A-then-B order, shared test runtime, incomplete native child traces, incompatible usage counters, different timing provenance/preparation boundaries and remaining review-detail asymmetry prohibit strong efficiency or causal superiority claims. The held-out suite cannot exhaust all permitted input combinations; notably A's shared-UID issue was found by review rather than that suite. Both public-only Testers misinterpreted a compatibility detail, and A also guessed the dispatch signature incorrectly. B's repair adapter failed to accommodate legitimate multi-module repair deltas. These shortcomings belong in the evidence rather than being silently repaired after outcomes.

The task is meaningfully harder than Stage 27 and supplies stronger behavioral, mutation and actual permission evidence, but **a clean end-to-end acceptance comparison was not achieved**. Candidate success, test-oracle quality, adapter reliability and architectural guarantees must remain separate.

## 14. Comparison with Stage 27

Stage 27 established comparable final code quality on its SQL splitter but suffered an adapter cleanup failure, asymmetric review, shared runtime support and incompatible usage. Stage 28's cleanup correction worked, preserved rejected repair bytes, measured incremental mutation detections despite red suites, and directly tested actual Reviewer write enforcement. Both Reviewers now inspect complete source trees and frozen test harnesses, but result-detail symmetry remains incomplete.

Both stages show native role orchestration can produce useful, independently testable engineering work. Both show stronger tested role restrictions in the custom workflow. Stage 28 adds real reviewer-detected candidate defects and demonstrates that flawed independent assertions can reward a regression. Its new repair-adapter rejection again prevents treating B's operational result as a clean measurement of the unchanged framework. Stage 27's inconclusive result is not an architectural failure; neither is Stage 28's.

## 15. Architectural implications and decision

| Option | Assessment across Stages 27 and 28 |
|---|---|
| **KEEP** | Not justified for the whole framework. No clear, repeatable engineering or valid operating-cost advantage has been demonstrated. Tested isolation benefits are real but do not alone justify all complexity. |
| **SIMPLIFY** | Plausible direction: native orchestration achieves comparable bounded engineering results, while explicit role permissions, artifact preservation and frozen behavioral evaluation have demonstrated value. Shared runtime support and failed/asymmetric workflow evidence prevent making it the established decision. |
| **REPLACE** | Not justified. The custom mechanisms provide meaningful tested restrictions, and native-only removal of the shared runtime has not been evaluated. |
| **INCONCLUSIVE** | **Selected.** Engineering equivalence on frozen checks is supported; reliable complete-architecture efficiency/reliability equivalence is not. |

The custom framework has **not yet demonstrated that its full additional complexity earns measurable engineering value over native orchestration**. Selected controls demonstrably matter, but these experiments do not establish that the whole framework is necessary to obtain them. Conversely, native delegation alone does not supply the tested guarantees automatically. No statistical superiority claim follows from these two experiments. This report recommends no architectural implementation change within Stage 28.

## Integrity and delivery

The [final integrity audit](docs/stage28-verification/final-integrity.json) confirms unchanged original HEAD/branch, raw index hash, staged/working diffs, status and tracked/nonignored-untracked file hashes; unchanged active framework source; unchanged effective frozen task/rubric/evaluator/dependencies/adapter; and unchanged reused Stage 27 adapter. The original invalid evaluator/freeze are preserved separately. Owned role repositories, PostgreSQL and extracted runtime were cleaned after artifact collection. [Cleanup receipt](docs/stage28-verification/runtime-cleanup.json).

Final patch SHA-256: A **`e03972361ac75957a39ee2eacc846525d4765f9c838c0d41687141b3b320650b`**; B **`988354306de34473e53874555c38a27b2981f08a4d7272dfe29d796d5fdbdbd7`**.

The compact [Stage 28 delivery archive](docs/stage28-verification/stage28-delivery.zip) contains baseline source, both patches, frozen contract/suites/designs, original failures, review/role evidence, relevant logs, JUnit/evaluation results, runtime/source manifests and this report. [Reproduction instructions](docs/stage28-verification/REPRODUCE.md) allow functional evaluation without rerunning models. The delivery receipt verifies ZIP CRCs and member hashes. No production data, credentials, extracted dependencies or database files are included.
