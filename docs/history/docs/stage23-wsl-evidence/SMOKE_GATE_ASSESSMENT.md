# Stage23 — Native Codex Execution Backend Assessment

**WSL SMOKE GATE PASS — 3 / 3 usable executions. Stage23 overall remains incomplete.**

On 2026-10-07, three fresh isolated Ubuntu WSL2 native Codex executions resolved `gpt-6.1-sol`, produced the exact required candidate, preserved all other repository bytes, and cleaned up successfully. Each Controller-generated handoff derives from artifacts. The successful Stage23B prerequisite is separate and is not counted among these three trials.

This continuation covers the three-smoke gate authorized by the user after Stage23B. Tester and later multi-agent phases have not run, respecting the latest instruction to defer those trials. Default routing and the custom transport remain unchanged. No Stage24 or OML work started.

The initial failed Windows attempt is preserved in [the historical assessment](docs/stage23-evidence/INITIAL_WINDOWS_ASSESSMENT.md). [Stage23A](STAGE23A_NATIVE_RUNTIME_PREREQUISITES.md) subsequently distinguished the sandbox OS user's unauthenticated state from the authenticated normal Windows user; [Stage23B](STAGE23B_WSL_NATIVE_SMOKE.md) established supported native Linux authentication and corrected WSL permissions. The initial assessment's login conclusion is historical, not the current host state.

## A. Native Codex discovery

- WSL2 Ubuntu 26.04 LTS, kernel `6.6.87.2-microsoft-standard-WSL2`, Linux user `ivan`.
- Executable `/home/ivan/.local/bin/codex`, resolving to `/home/ivan/.codex/packages/standalone/releases/0.160.1-x86_64-unknown-linux-musl/bin/codex`; **codex-cli 0.160.1**.
- Supported non-interactive invocation: `codex --no-daemon -a never exec --ignore-user-config --ephemeral --color never --cd <isolated-repository> --model gpt-6.1-sol -`, with prompt on stdin. Exact argv appears in every receipt.
- Effort `low`, selected through `-c model_reasoning_effort="low"`; web search and native subagents disabled. Fresh exec is used, without resume or fork.
- Supported native `codex debug models` exposes `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-reserve`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, and `codex-auto-review`. [Catalog](docs/stage23-wsl-evidence/smoke-1/native-models.json).
- Exact inference-resolved identifier: **`gpt-6.1-sol`**, provider `openai`, confirmed by the native CLI banner and valid model-produced edits in all three runs.
- Native supported Linux ChatGPT device sign-in completed. `codex login status` succeeds. Controller does not read/copy/export credentials; native Codex owns authentication. Inherited API credentials and chat identifiers are excluded from execution environment.
- Standard CLI output is transient; only banner model/session/provider/sandbox fields and Controller artifact evidence are retained. Reasoning and final narration are discarded. Every trial exited 0; failure exit codes alone never establish artifact validity.

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
  → disposable role repository is removed
```

This path contains no custom model client, relay, OAuth parser, streaming-frame implementation or tool-result continuation protocol. The next-role boundary is prepared through explicit Controller artifacts, but a fresh Tester has not yet consumed it. No production default has migrated.

## C. Production changes

No existing production transport, routing or Windows sandbox configuration changed in this continuation. The earlier `agent_system/native_codex.py` remains an experimental Windows helper; these WSL trials use the proven Stage23B invocation directly rather than claiming that the Windows helper works.

Added/modified for this continuation:

- `validation/stage23_wsl_smoke.py`: bounded three-trial sequential WSL gate, distinct session/workspace checks, archive verification and Controller-generated handoffs; stops on an unusable trial.
- `validation/stage23b_wsl_smoke.py`: reused validated native invocation; accepts Controller evidence/trial identity, records immutable baseline hashes and fresh context metadata, rejects linked files, and classifies successful artifact results without narration.
- `docs/stage23-wsl-evidence/`: frozen input/stub, three catalog/role receipts, three retained candidates, three canonical handoffs, and gate summary.
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

**0 / 3 run.** Smoke prerequisites now pass. Independent Tester design, schema/domain validation, freeze/hash before candidate exposure, and deterministic execution of frozen tests remain required. No Tester execution or candidate exposure occurred in this continuation.

## F. Reviewer trials

**0 / 2 run.** Await the three trustworthy minimal workflows. Reviewer value remains unmeasured.

## G. Architect trials

**0 / 2 run.** Await Reviewer stability. Architect contract normalization/value remain unmeasured.

## H. Full workflow

**0 / 1 run.** Largest completed chain: Controller → native Implementer → artifact verification → canonical handoff → cleanup. Cross-role workflow acceptance remains unproven. No Data Auditor was applicable or invoked.

## I. Model use

| Model | Successful inference executions in this three-smoke gate |
|---|---:|
| GPT-6.1 Sol (`gpt-6.1-sol`) | **3** |
| GPT-5.6 Sol | **0** |
| Astra | **0** |

Stage23B separately completed one GPT-6.1 Sol prerequisite execution. The historical Windows attempt failed before inference. Catalog and sandbox preflight commands do not count as inference runs. Native internal request counts and monetary cost are not observable here and are not estimated.

## J. Failure/recovery evidence

Current gate: three normal completions, zero native timeouts, zero unrecoverable trials, zero live abnormal recoveries. No candidate required failure recovery. Normal artifacts remain available after execution and cleanup.

Earlier Stage23B preflights failed before inference: the file-scoped writable mount triggered a native bubblewrap error; the standalone Codex release directory was absent from minimal runtime reads; and a repository under explicitly denied `/tmp` was inaccessible. The corrected configuration writes the isolated `src` directory, reads the installed release directory, and places disposable repositories under the Linux home. Historical receipts remain in `docs/stage23b-evidence/`; all those repositories were cleaned up. No Windows permission was broadened.

The earlier Windows helper has 25 recorded focused offline checks with Stage22 artifact checks. Those historical fixtures do not certify WSL containment or live abnormal recovery. This continuation's verification is the requested three live trials and independent candidate/hash/handoff inspection, not a new full-suite claim.

## K. Isolation

- Native sessions: `01a11610-4927-7920-8aa3-8512051f0b03`, `01a11610-8350-7571-8694-0d6435617e57`, `01a11610-b313-7e40-959a-089cadf0d6a6`. Three distinct workspaces and sessions verified by Controller.
- Each starts a new dedicated ephemeral exec with only explicit role input and a fresh stub. No session resume/fork, chat history, previous candidate, subagent or inherited app pipe is supplied. Shared native authentication is kept outside role context.
- Native permissions: minimal runtime reads, read-only installed Codex release directory and repository, write access limited to the isolated `src` directory; project network disabled, `/tmp` and `$TMPDIR` denied. No `:root` grant, full-access mode or sandbox bypass. Directory write access permits creating files inside `src`; exact full-tree validation rejects any such extra mutation.
- Each preflight confirms target write access, refused write-open for role input and Git config, correct cwd, and unchanged bytes. The exact full-tree comparison after execution includes Git metadata; only the target changed. Linked entries are rejected.
- All three disposable repositories were deleted and absence checked. Controller evidence remains outside role-readable paths. Native CLI processes exited normally before artifact collection/cleanup. This checks repository scope, not an exhaustive audit of all host/runtime filesystem changes.
- Tester candidate blindness and cross-role independence still require the next phase; three independent Implementer contexts alone do not prove them.

**Docker:** these bounded tasks work with native WSL permissions and isolated repositories, without Docker around inference. Exact-byte checks do not execute arbitrary candidate code. General project-command isolation and deterministic Tester execution are separate questions; Docker requirements for broader tasks remain undecided. No native-to-Docker relay was built.

## L. Complexity comparison

| Property | Preserved custom backend | Native WSL path observed here |
|---|---|---|
| Model surface | Prior limited catalog omitted requested 6.1 Sol | Catalog and three executions confirm gpt-6.1-sol |
| Authentication | Custom plan-auth transport participates in Controller path | Native Linux Codex sign-in; no Controller credential handling |
| Protocol/tool ownership | Custom upstream/relay/session/tool responsibilities | Supported executable owns inference and tool loop |
| Artifact reliability | Prior Stage22 evidence remains its own sample | 3 / 3 exact usable single-role artifacts |
| Isolation | Prior Docker/action boundaries | Native WSL sandbox preflights and exact repository comparisons pass |
| Cleanup | Prior-stage receipts | 3 / 3 repositories removed; evidence recoverable |
| Workflow complexity | Existing role/transport code remains | Bounded native launcher reuse plus sequential Controller gate; later role flow unvalidated |

Native execution removes custom protocol responsibilities from this tested path. Three tiny smoke runs establish that path's operation, but do not establish superior production reliability, full workflow reliability, cost, or the complete Stage23 success criterion.

## M. Recommended backend

**Native Codex remains experimental; WSL is the validated runtime for the next Stage23 phase.** Keep existing production defaults and old transport until cross-role gates pass. The single-role smoke blocker is resolved. Stage23 itself is not yet PASS.

## N. Recommended role routing

The next authorized validation phase should use exact `gpt-6.1-sol` for Implementer and independent Tester, with fresh contexts and Controller-owned frozen acceptance. Reviewer and Architect remain sequentially gated afterward. No cheaper production routing or full migration recommendation follows from single-role smoke evidence alone. Stop here before deferred multi-agent trials and Stage24.
