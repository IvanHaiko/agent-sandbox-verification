# Stage23 — Native Codex Execution Backend Assessment

**WSL SMOKE GATE PASS — 3 / 3. MINIMAL WORKFLOW GATE PASS — 3 / 3. Stage23 overall remains incomplete.**

On 2026-10-07, three fresh isolated Ubuntu WSL2 native Codex executions resolved `gpt-6.1-sol`, produced the exact required candidate, preserved all other repository bytes, and cleaned up successfully. Each Controller-generated handoff derives from artifacts. The successful Stage23B prerequisite is separate and is not counted among these three trials.

The subsequently authorized Implementer → independent Tester phase completed three fresh workflows with **70 / 70 frozen cases passing** (24, 23, 23). All six roles used `gpt-6.1-sol` and fresh contexts. Schema/domain validation, candidate blindness, freeze-before-exposure, deterministic acceptance and cleanup passed. Reviewer and later phases have not run. Default routing and the custom transport remain unchanged. No Stage24 or OML work started.

The initial failed Windows attempt is preserved in [the historical assessment](docs/stage23-evidence/INITIAL_WINDOWS_ASSESSMENT.md). [Stage23A](STAGE23A_NATIVE_RUNTIME_PREREQUISITES.md) subsequently distinguished the sandbox OS user's unauthenticated state from the authenticated normal Windows user; [Stage23B](STAGE23B_WSL_NATIVE_SMOKE.md) established supported native Linux authentication and corrected WSL permissions. The initial assessment's login conclusion is historical, not the current host state.

## A. Native Codex discovery

- WSL2 Ubuntu 26.04 LTS, kernel `6.6.87.2-microsoft-standard-WSL2`, Linux user `ivan`.
- Executable `/home/ivan/.local/bin/codex`, resolving to `/home/ivan/.codex/packages/standalone/releases/0.160.1-x86_64-unknown-linux-musl/bin/codex`; **codex-cli 0.160.1**.
- Supported non-interactive invocation: `codex --no-daemon -a never exec --ignore-user-config --ephemeral --color never --cd <isolated-repository> --model gpt-6.1-sol -`, with prompt on stdin. Exact argv appears in every receipt.
- Effort `low` for the smoke gate and `medium` for both roles in the minimal workflow gate, selected through `-c model_reasoning_effort`. Web search and native subagents are disabled. Fresh exec is used, without resume or fork.
- Supported native `codex debug models` exposes `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-reserve`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and `codex-auto-review`. [Catalog](docs/stage23-wsl-evidence/smoke-1/native-models.json).
- Exact inference-resolved identifier: **`gpt-6.1-sol`**, provider `openai`, confirmed by the native CLI banner and valid model-produced edits in all three runs.
- Native supported Linux ChatGPT device sign-in completed. `codex login status` succeeds. Controller does not read/copy/export credentials; native Codex owns authentication. Inherited API credentials and chat identifiers are excluded from execution environment.
- Standard CLI output is transient; only banner model/session/provider/sandbox fields and Controller artifact evidence are retained. Reasoning and final narration are discarded. All nine successful Stage23 role executions exited 0; failure exit codes alone never establish artifact validity.

Supported behavior was checked against official [non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode), [permission profiles](https://learn.chatgpt.com/docs/permissions), and installed CLI help. Model access is established by live local execution, rather than by public documentation alone.

## B. Architecture

```text
Controller prepares fresh Linux repository and explicit frozen role input
  → native sandbox preflight verifies workspace and write boundaries
  → fresh ephemeral native Codex exec using gpt-6.1-sol
  → Codex owns authentication, inference, tool loop and execution
  → owned process exits
  → Controller compares every repository file, including Git metadata
  → Controller checks exact candidate bytes, hashes, archives and diffs
  → Controller generates implementation handoff; candidate remains unaccepted
  → Implementer repository is removed
  → fresh blind Tester repository: contract/schema, no implementation or candidate
  → fresh ephemeral native Tester writes structured test-design artifact
  → Controller validates schema, ASCII domain and IDs
  → freeze/hash exact design and generated fixed harness; Tester exits and is cleaned up
  → candidate is exposed to a separate Controller acceptance repository
  → native read-only sandbox executes the frozen harness without model inference
  → Controller verifies unchanged candidate/tests, decides acceptance and cleans up
```

This path contains no custom model client, relay, OAuth parser, streaming-frame implementation or tool-result continuation protocol. Tester receives no Implementer handoff or candidate during design. Only Controller acceptance consumes the candidate after freeze. The handoff and final decision come from artifacts, never role narration. Native exec is allowed to end normally; no additional summary/finalization session is requested. No production default has migrated.

## C. Production changes

No existing production transport, routing or Windows sandbox configuration changed. The earlier `agent_system/native_codex.py` remains an experimental Windows helper. The new opt-in Linux process helper applies the proven Stage23B invocation to the required two roles; it contains no model protocol or custom sandbox implementation.

Added/modified for this continuation:

- `validation/stage23_wsl_smoke.py`: bounded three-trial sequential WSL gate, distinct session/workspace checks, archive verification and Controller-generated handoffs; stops on an unusable trial.
- `validation/stage23b_wsl_smoke.py`: reused validated native invocation; accepts Controller evidence/trial identity, records immutable baseline hashes and fresh context metadata, rejects linked files, and classifies successful artifact results without narration.
- `agent_system/native_codex_linux.py`: narrow native Linux launcher, existing permission profile, native sandbox preflight, owned process-group completion/timeout handling, exact mutation scope and artifact verification. Existing default runner selection is untouched.
- `validation/stage23_wsl_workflow.py`: three sequential Implementer → blind Tester trials, artifact handoff, freeze/hashes, Controller acceptance and checked cleanup. Stops at the first failed trial; no model retries or repairs.
- `validation/stage23_labels_contract.py`: extracts the unchanged prior labels task/schema and Controller harness/interpreter without importing legacy transport; strict structured artifact/domain validation and AST interface check. Fixed harness uses `runpy` under isolated Python in the native sandbox.
- `validation/test_stage23_wsl_workflow.py`: five offline guard checks for frozen test integrity, supported domain, duplicate JSON/IDs, incorrect candidate and precise ValueError expectation handling.
- `docs/stage23-wsl-evidence/`: frozen input/stub, three catalog/role receipts, three retained candidates, three canonical handoffs, and gate summary.
- `docs/stage23-wsl-evidence/minimal/`: frozen task and executed source, six role receipts/inputs, three candidates/handoffs/designs/harnesses/freezes/exposures/acceptance results, final decisions, summary, offline checks and independent integrity/contract-consistency audits. The previous smoke-only assessment is preserved as `SMOKE_GATE_ASSESSMENT.md` in the parent evidence directory.
- `docs/stage23-evidence/INITIAL_WINDOWS_ASSESSMENT.md`: preserved prior assessment.
- This assessment and Stage23B readiness cross-reference.

The shared project root is not a Git repository. No commit or PR is claimed. Each role repository had independently initialized Git metadata.

## D. Smoke trials

Frozen task: implement `def add_one(value: int) -> int` using exactly `return value + 1`. Only `src/add_one.py` may change. Each trial starts with the same frozen stub and role input, not with another trial's candidate.

| Trial | Resolved model | Effort | Exit | Execution status | Changed files | Seconds | Cleanup |
|---|---|---|---:|---|---|---:|---|
| [smoke-1](docs/stage23-wsl-evidence/smoke-1/smoke.json) | gpt-6.1-sol | low | 0 | completed | src/add_one.py only | 14.652 | passed |
| [smoke-2](docs/stage23-wsl-evidence/smoke-2/smoke.json) | gpt-6.1-sol | low | 0 | completed | src/add_one.py only | 11.986 | passed |
| [smoke-3](docs/stage23-wsl-evidence/smoke-3/smoke.json) | gpt-6.1-sol | low | 0 | completed | src/add_one.py only | 11.557 | passed |

**3 / 3 usable; no failed trial or retry within this gate.** All candidates are byte-identical to the frozen expected module. SHA-256: `cbb9d566186943a504d0d8de0ff291eb4bcbc753fd36505065470d3f8e395565`. Archives were read and hashed after process exit, then independently hashed with Windows `Get-FileHash` after role repository cleanup.

[Gate summary](docs/stage23-wsl-evidence/smoke-summary.json) includes full trial records, baseline hashes, native argv, distinct identities and Controller verification. Each trial directory contains `candidate.py` and `implementer-handoff.json`. Handoffs record observed model, execution status, exact hash/diff, interface/scope checks and `candidate_status: unaccepted`; Implementer prose has no authority.

## E. Minimal multi-agent trials

**3 / 3 trustworthy workflows completed and accepted.** The exact prior Stage22 `normalize_labels` contract was retained: ASCII comma/quote/escape parsing, protected versus ordinary whitespace, normalization, deduplication, and whole-input errors. No candidate from the smoke task or prior stage was reused.

| Trial | Implementer seconds / exit | Tester seconds / exit | Frozen cases passed | Acceptance | Cleanup |
|---|---|---|---:|---|---|
| [minimal-1](docs/stage23-wsl-evidence/minimal/minimal-1/assessment.json) | 24.758 / 0 | 95.357 / 0 | 24 / 24 | PASS | all 3 repositories removed |
| [minimal-2](docs/stage23-wsl-evidence/minimal/minimal-2/assessment.json) | 28.673 / 0 | 88.898 / 0 | 23 / 23 | PASS | all 3 repositories removed |
| [minimal-3](docs/stage23-wsl-evidence/minimal/minimal-3/assessment.json) | 28.016 / 0 | 105.036 / 0 | 23 / 23 | PASS | all 3 repositories removed |

Every role resolved `gpt-6.1-sol` with `medium` effort; six distinct session IDs are in [the summary](docs/stage23-wsl-evidence/minimal/summary.json). They are distinct from the earlier smoke and prerequisite sessions.

| Trial | Candidate SHA-256 | Frozen independent design SHA-256 |
|---|---|---|
| minimal-1 | `0b68590187179e355f86587d774eda9658a78a9375672aa96aa89fcbc3923b85` | `358b4182f6f7e104ea8d71007751a90225c91aed6c9fef42150d03ab982bd282` |
| minimal-2 | `f32063da0e7e4a1f9f640ebd2ea95e0d171308a45e6ffa893d07e0dd0e92ed1e` | `964bd916e933ac61153870811fd59cb3840ddd4ece249b1f1d6f9d821d86c1f3` |
| minimal-3 | `7a6a61e715bf6323fe4087d76571c67b833a1703a306c2c4f803ac0ef8a094c7` | `2c41569474b814d0f0d55f33bdfa0bea080b180bf6d5a9dceb7b5cc0934476f1` |

Tester writes data, not executable tests. Controller validates the unchanged schema, explicit ASCII domain, unique IDs and inputs, then freezes the exact JSON and fixed generated harness before exposure. Tester has already exited and its repository is removed when the candidate reaches the separate Controller acceptance repository. Acceptance runs `/usr/bin/python3 -I -B` through supported `codex sandbox`, with no writable subtree or project network. All cases, selected properties and runtime interface checks passed; complete repository bytes and all frozen artifact hashes remained unchanged.

[Independent integrity audit](docs/stage23-wsl-evidence/minimal/integrity-audit.json) rechecked freeze/exposure ordering, archive hashes, unchanged candidate/tests, six fresh sessions, unchanged executed source and absence of all nine disposable repositories. [Contract consistency check](docs/stage23-wsl-evidence/minimal/contract-consistency.json) found no mismatch between any of the 70 Tester expectations and the preexisting frozen Controller contract interpreter. That check did not edit expectations or supply acceptance cases. Model calls during Controller acceptance: **0**; extra Tester narration sessions: **0**. No retries, repairs or test expectation changes were needed.

## F. Reviewer trials

**0 / 2 run.** The minimal stability prerequisite now passes. Reviewer value remains unmeasured; the next phase requires two fresh review-chain trials.

## G. Architect trials

**0 / 2 run.** Await Reviewer stability. Architect contract normalization/value remain unmeasured.

## H. Full workflow

**0 / 1 required full-chain trial run.** Largest completed chain: Controller → native Implementer → artifact handoff → blind independent Tester → frozen tests → Controller deterministic acceptance → final decision → cleanup. Three instances passed. Architect and Reviewer are absent; their full-chain gates remain outstanding. No Data Auditor was applicable or invoked.

## I. Model use

| Model | Successful inference executions in Stage23 smoke + minimal gates |
|---|---:|
| GPT-6.1 Sol (`gpt-6.1-sol`) | **9** (3 smoke, 3 Implementer, 3 Tester) |
| GPT-5.6 Sol | **0** |
| Astra | **0** |

Stage23B separately completed one GPT-6.1 Sol prerequisite execution. The historical Windows attempt failed before inference. Catalog and sandbox preflight commands do not count as inference runs. Native internal request counts and monetary cost are not observable here and are not estimated.

## J. Failure/recovery evidence

Current smoke and minimal gates: nine normal role completions, zero native timeouts, zero unrecoverable trials, zero live abnormal recoveries. No candidate required failure recovery. Normal artifacts and frozen designs remain available after execution and cleanup. Live abnormal recovery is still unproven and is not inferred from these normal successes.

Earlier Stage23B preflights failed before inference: the file-scoped writable mount triggered a native bubblewrap error; the standalone Codex release directory was absent from minimal runtime reads; and a repository under explicitly denied `/tmp` was inaccessible. The corrected configuration writes the isolated `src` directory, reads the installed release directory, and places disposable repositories under the Linux home. Historical receipts remain in `docs/stage23b-evidence/`; all those repositories were cleaned up. No Windows permission was broadened.

The earlier Windows helper has 25 recorded focused offline checks with Stage22 artifact checks. Those historical fixtures do not certify WSL containment or live abnormal recovery. This continuation additionally passed **five focused offline guard tests**, then three live workflows and independent hash/order/cleanup audits. [Offline receipt](docs/stage23-wsl-evidence/minimal/offline-checks.json). No new full-suite pass is claimed.

## K. Isolation

- Native sessions: `01a11610-4927-7920-8aa3-8512051f0b03`, `01a11610-8350-7571-8694-0d6435617e57`, `01a11610-b313-7e40-959a-089cadf0d6a6`. Three distinct workspaces and sessions verified by Controller.
- Each starts a new dedicated ephemeral exec with only explicit role input and a fresh stub. No session resume/fork, chat history, previous candidate, subagent or inherited app pipe is supplied. Shared native authentication is kept outside role context.
- Native permissions: minimal runtime reads, read-only installed Codex release directory and repository, write access limited to the isolated `src` directory; project network disabled, `/tmp` and `$TMPDIR` denied. No `:root` grant, full-access mode or sandbox bypass. Directory write access permits creating files inside `src`; exact full-tree validation rejects any such extra mutation.
- Each preflight confirms target write access, refused write-open for role input and Git config, correct cwd, and unchanged bytes. The exact full-tree comparison after execution includes Git metadata; only the target changed. Linked entries are rejected.
- All three disposable repositories were deleted and absence checked. Controller evidence remains outside role-readable paths. Native CLI processes exited normally before artifact collection/cleanup. This checks repository scope, not an exhaustive audit of all host/runtime filesystem changes.
- Minimal workflows used six further distinct ephemeral sessions and isolated repositories. Tester repositories have no `src` directory, candidate or implementation stub. Native preflight refused read-open for the candidate archive and Implementer handoff in Controller evidence. The saved Tester input contains only the original contract, criteria, domain and schema. Full mutation comparison permits only `tests/test-design.json` to change.
- Each test design and generated harness is frozen after Tester shutdown and before candidate exposure. The candidate reaches a separate Controller acceptance repository; no second Tester session is started. Before/after acceptance hashes verify the same candidate and same frozen tests. All nine minimal role/acceptance repositories were deleted and independently checked absent; no native role session was reused from earlier gates.

**Docker:** these bounded tasks work with native WSL permissions and isolated repositories, without Docker around inference. Smoke uses exact-byte checks; the minimal workflow executes candidate code only inside supported native read-only command sandboxing, with project network disabled and bounded process time. No custom sandbox or native-to-Docker relay was built. This demonstrates the fixed Python contract/harness case, not suitability for arbitrary dependency-heavy or untrusted project workloads; Docker needs for those workloads remain undecided.

## L. Complexity comparison

| Property | Preserved custom backend | Native WSL path observed here |
|---|---|---|
| Model surface | Prior limited catalog omitted requested 6.1 Sol | Catalog and three executions confirm gpt-6.1-sol |
| Authentication | Custom plan-auth transport participates in Controller path | Native Linux Codex sign-in; no Controller credential handling |
| Protocol/tool ownership | Custom upstream/relay/session/tool responsibilities | Supported executable owns inference and tool loop |
| Artifact reliability | Prior Stage22 evidence remains its own sample | 3 / 3 smoke artifacts and 3 / 3 accepted independent-test workflows |
| Isolation | Prior Docker/action boundaries | Native WSL sandbox preflights and exact repository comparisons pass |
| Cleanup | Prior-stage receipts | 3 smoke + 9 minimal repositories removed; artifacts recoverable |
| Workflow complexity | Existing role/transport code remains | One native process per role plus Controller artifact/freeze/acceptance logic; later role phases unvalidated |

Native execution removes custom protocol responsibilities from this tested path. The observed single-role and independent-test workflows pass their gates, but do not establish superior production reliability, complete role-chain reliability or cost. The old and new samples use different models and are not a controlled performance/reliability comparison. Complete Stage23 success criteria remain unmet until the later role gates pass.

## M. Recommended backend

**Native Codex remains experimental; WSL is the validated runtime for further Stage23 trials.** Both smoke and Implementer → independent Tester gates now pass. Keep existing production defaults and old transport until Reviewer, Architect and representative full-chain evidence exists. Stage23 itself is not yet PASS.

## N. Recommended role routing

The validated route for Implementer and independent Tester is exact `gpt-6.1-sol` with `medium` effort and fresh contexts; the observed three-trial sample supports continuing the same route for this bounded validation. The next phase is two Reviewer-chain trials using exact `gpt-6.1-sol`, then gated Architect and representative full-chain trials. No cheaper production routing, Reviewer/Architect value judgment or full migration recommendation follows yet. This authorized minimal phase stops here; Reviewer and Stage24 were not automatically started.
