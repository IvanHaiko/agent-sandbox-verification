# Stage23 — Native Codex Execution Backend Assessment

**STOPPED_AT_NATIVE_SMOKE_STARTUP — Stage23 did not pass.**

On 2026-10-07, the installed native runtime listed `gpt-6.1-sol`, but the first bounded smoke invocation exited before creating a thread or changing the target. A supported native configuration probe identified the error: **failed to prepare Windows sandbox wrapper: open sandbox provisioning pipe**. The current execution boundary cannot provision the requested native sandbox. CLI login status also reported **Not logged in**; authenticated inference access remains unverified. Neither catalog visibility nor this assessment proves account access to inference.

The requested stop condition was honored. No further smoke attempts, Tester, Reviewer, Architect, Data Auditor, full-chain runs, alternate model, credential extraction, OAuth change, new relay, Stage24, OML work, or default backend replacement followed. Disposable role storage was removed. The legacy backend is preserved.

## A. Native Codex discovery

- Executable: `C:\Users\4ivan\AppData\Local\OpenAI\Codex\bin\5ea220ae823df3d7\codex.exe`.
- Version: **codex-cli 0.160.1**. Local help was inspected for the root command, `exec`, `app-server`, schema generation, and the installed native daemon/proxy controls. No daemon was restarted or existing chat changed.
- Non-interactive mechanism: supported `codex exec`; prompt can be supplied on stdin. `--no-daemon` selects a dedicated process, `--ephemeral` avoids persisted role rollouts, and neither resume nor fork is used.
- Model selection: `--model gpt-6.1-sol`. Reasoning control: `-c model_reasoning_effort="low"`. Workspace selection: `--cd <isolated-repository>`.
- Output: supported JSONL lifecycle/action events. Controller consumes only lifecycle and action metadata, discarding raw command output, narration and reasoning. Required artifact bytes are inspected after shutdown. Process exit status is independent of artifact usability.
- Observed exit behavior: smoke startup returned **1**, catalog discovery returned **0**, and the config-only app-server process returned **0** despite `thread/start` returning RPC error **-32603**. Process success alone is not role success.
- Catalog query: documented native `initialize` / `initialized` / `model/list` over the executable's supported app-server stdio interface. This was discovery only; it did not use the custom plan transport or start inference. Pagination and hidden entries were included.
- Visible identifiers: `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`. Hidden entries: `gpt-daybreak-blue-latest`, `gpt-daybreak-red-latest`, `codex-auto-review`.
- Exact requested native identifier: **`gpt-6.1-sol`**. Returned efforts: low, medium, high, xhigh, max, ultra; returned default: low. Smoke selected low; delegation was disabled. The identifier was listed and explicitly requested, **not resolved by a successful inference execution**.
- Authentication ownership: native Codex. Controller did not read, copy, log, or export auth files or tokens. `CODEX_HOME`, if set, remains native-owned. Inherited API keys and chat identifiers are excluded from the role launcher environment. CLI's supported login-status command reported no login; no login flow was initiated.

[Native discovery](docs/stage23-evidence/native-discovery.json), [startup diagnostic](docs/stage23-evidence/native-startup-diagnostic.json). Supported interfaces were checked against official [non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode), [App Server documentation](https://learn.chatgpt.com/docs/app-server), and [permission profiles](https://learn.chatgpt.com/docs/permissions); the installed binary's help/schema determined actual flags. Public model documentation is not evidence of this account's inference access.

## B. Architecture

```text
Controller prepares an isolated repository and explicit role input
  → dedicated native Codex exec, exact model, ephemeral context
  → native Codex owns authentication, model loop and tools
  → completed native tool artifact boundary / process exit
  → Controller verifies scope, exact bytes, hashes, diff and contract
  → Controller-generated handoff with candidate still unaccepted
  → cleanup
  → fresh next role, only explicitly permitted artifacts
```

The new opt-in boundary invokes the installed executable directly. It contains no HTTP model client, plan-auth adapter, OAuth parser, Responses frame handler, relay, tool-result continuation loop or provider retry logic. The old implementations are retained. Their responsibilities are absent from this new path; **no default production responsibility has been migrated yet**.

Implementer usability comes from checked artifacts, never final prose. The runner observes a successful native completed-tool event, validates the required artifact and ends its owned process tree. After shutdown it repeats full mutation-scope and exact artifact checks and records hashes/diff. Authentication, model, sandbox, unknown failures, bad scope, incomplete writes or unconfirmed tree shutdown cannot recover. A known timeout or Controller stop at a verified completed-tool boundary may be `abnormal_recoverable`; this is covered offline, not proven live here. The CLI did not reach that boundary in this trial.

Native JSON events do not establish an inference-resolved model in the observed run. Evidence reports `resolved_model` as unavailable rather than treating a requested flag as successful model resolution. No canonical implementation handoff or promotion was produced from the failed smoke.

## C. Production changes

New production file:

- `agent_system/native_codex.py`: experimental `NativeCodexRunner`, explicit native invocation, fresh context/environment, native permission profile, lifecycle/action observation, owned shutdown, artifact validation and evidence. It is an opt-in execution helper, not a newly selected default runner or a complete validated orchestration chain.

New validation/test files:

- `validation/stage23_discovery.py`: native catalog-only discovery and sanitized receipt.
- `validation/stage23_smoke.py`: three-trial sequential smoke gate, frozen bounded input, whole-module AST check, exact-byte archive and checked cleanup; stops on the first unusable attempt.
- `tests/test_native_codex.py`: offline process/artifact and launcher-policy checks. Process-tree success is simulated through a fixture process handle; native containment is explicitly not certified by these tests.
- `docs/stage23-evidence/`: catalog, smoke receipt/summary, frozen input/baseline, configuration diagnostic, focused check results and final cleanup receipt.
- This assessment.

No existing production source, routing configuration, OAuth, transport or prior assessment was edited. The shared project root is not a Git repository. No commit or PR is claimed; the smoke workspace was a disposable initialized repository.

## D. Smoke trials

Frozen task: inspect `role-input.md` and `src/add_one.py`, then implement `def add_one(value: int) -> int` with the single statement `return value + 1`. Only that target may change. The Controller checks the entire module AST against the frozen contract without executing model-generated host code.

| Trial | Native model requested | Effort | Exit | Status | Changed files | Artifact hashes | Elapsed | Cleanup |
|---|---|---|---:|---|---|---|---:|---|
| smoke-1 | gpt-6.1-sol | low | 1 | unrecoverable; native sandbox startup failure | none | none | 0.844 s | passed |
| smoke-2 | — | — | — | not started after failed gate | — | — | — | no workspace created |
| smoke-3 | — | — | — | not started after failed gate | — | — | — | no workspace created |

**Usable: 0 / 1 attempted; required 3 / 3 was not achieved.** The first process produced no native thread ID, tool actions, candidate or inference-resolved model. The unchanged stub is not counted as a candidate. No abnormal recovery predicate passed. All per-execution identity, invocation, scope, timing and cleanup data available for this attempt is in [smoke-1.json](docs/stage23-evidence/smoke-1.json). [Summary](docs/stage23-evidence/smoke-summary.json), [input](docs/stage23-evidence/smoke-input.md), [baseline](docs/stage23-evidence/smoke-baseline.py).

## E. Minimal multi-agent trials

**0 started / 3 required.** The smoke gate blocked Implementer → independent Tester validation. No Tester design, freeze, candidate exposure or deterministic acceptance occurred. Prior-stage trials and offline fixtures do not count toward this requirement.

## F. Reviewer trials

**0 started / 2 required.** Minimal stability was not established. Reviewer material value is unmeasured.

## G. Architect trials

**0 started / 2 required.** Reviewer stability was not established. Architect value and Controller contract normalization are unmeasured.

## H. Full workflow

**0 started / 1 required.** Largest attempted chain: Controller → native Implementer process startup → failure → artifact inspection → cleanup. No role successfully completed. Data Auditor was not applicable or invoked.

## I. Model use

| Model | Role process launch attempts | Successful inference-backed role executions |
|---|---:|---:|
| GPT-6.1 Sol (`gpt-6.1-sol`) | 1 | 0 |
| GPT-5.6 Sol | 0 | 0 |
| Astra | **0** | **0** |

Catalog and no-turn configuration probes are discovery operations, not inference roles. Smoke failed before thread creation: no inference result or request count was observable. There is no evidence of a model request from this failed pre-thread attempt; no hidden internal request count or monetary estimate is asserted. Primary assistant implementation work and offline synthetic processes are outside trial-role accounting.

## J. Failure/recovery evidence

Live: one startup failure, zero Codex timeouts, zero live abnormal recoveries and one unrecoverable attempt. Native `thread/start` independently refused initialization while preparing sandboxed AGENTS instructions, with the provisioning-pipe error quoted above. No turn was requested by that diagnostic. Configuration parsing alone could start/exit the app-server, so parser acceptance does not demonstrate a usable native execution sandbox.

Offline: **25 focused tests passed**, combining new runner tests with existing Stage22 artifact tests. They exercise artifact survival after a simulated successful tree stop, rejection of authentication/unknown failures, scope contamination, missing/incomplete artifacts, unsuccessful tree stop, exact model/ephemeral CLI settings, native profile serialization and removal of inherited API credentials/chat IDs. Stage22 recovery checks remained intact. [JUnit receipt](docs/stage23-evidence/offline-checks.xml).

The first check command failed fixture setup because the shared OS temporary pytest directory was inaccessible. A workspace-owned `--basetemp` fixed setup. That run then exposed that `taskkill` is also unavailable from this restricted boundary: one offline recovery expectation failed (23 passed). The runner now refuses recovery when tree shutdown cannot be confirmed and immediately terminates its launcher handle; the final fixture explicitly models tree-stop success and tests refusal on failure. These are local checks, not additional live smoke attempts or evidence that Windows native containment works. No full-suite pass is claimed.

## K. Isolation

- The attempted role used `.test-tmp/stage23-native/smoke-1`, an independent repository containing only explicit input and a target stub. It did not share project Git metadata. Input/hash, exact argv and workspace identity are recorded.
- Invocation used fresh `exec`, `--ephemeral`, `--no-daemon`; no resume/fork or other role conversation was supplied. Inherited chat identifiers/app-tool pipe were excluded. No session successfully started, so successful cross-role independence remains unproven.
- Native profile requested minimal runtime reads, read access to the role workspace, write access only to the explicit target, and disabled command network. API credentials were excluded from inherited environment; native login files stayed outside role input. The native runtime refused provisioning before executing tools. No containment bypass or broadened host access was tried.
- No target or other workspace file changed; zero native actions were observed. This proves absence of mutation in this stopped attempt, not enforcement during a successful model run.
- Tester blindness before freeze is **not tested** because Tester was never invoked. There were no cross-role handoffs or exposed candidates.
- The native catalog/config processes exited; the smoke process exited with code 1. No existing app process was stopped. Role repository and generated schema/unit-test storage were removed; persistent evidence is Controller-owned. [Final cleanup](docs/stage23-evidence/final-cleanup.json).

**Docker assessment:** the new model-runtime boundary does not require Docker, a transport relay, or exported credentials. Project-command containment is a separate decision. This smoke uses an AST check and runs no candidate code, so no Docker project execution was needed. Native permissions must actually provision and pass read/write/isolation checks before claiming they can replace the old model-runtime container boundary. General untrusted project commands may continue to need Docker; no new native-to-Docker request bridge was built. The failed native isolation prerequisite prevents recommending removal of existing containment.

## L. Complexity comparison

| Property | Old custom path: preserved observed/source evidence | New native path: observed here |
|---|---|---|
| Model surface | Stage22 continuation catalog omitted requested 6.1 Sol | Native catalog lists gpt-6.1-sol; inference unverified |
| Authentication | Controller-integrated plan OAuth transport | Native runtime owns login; CLI reported no login |
| Model/tool protocol | Plan upstream, relay, protocol gate, native session/tool bridge | One direct CLI process; no model protocol or relay implementation |
| Artifact reliability | Stage22 obtained bounded candidates; later workflow/tester gates remained unstable | 0 usable native candidates; cannot claim equal or better reliability |
| Isolation | Prior admitted Docker/action boundaries | Native permission profile requested; provisioning failed |
| Cleanup | Prior assessments retain their cleanup evidence | One disposable repository removed; all owned startup processes ended |
| Workflow complexity | Transport-specific orchestration remains in legacy path | Narrow opt-in process/artifact helper; later role flow unimplemented after stop |
| Requests/cost | Prior recorded request counts remain prior-stage evidence | No successful inference, internal request count unavailable, no cost estimate |

Removing transport ownership is an architectural simplification visible in the new source. **Measurably simpler/reliable successful native workflow was not established**, so success criterion 15 is unmet. These unequal trial samples do not support a performance or reliability superiority claim.

## M. Recommended backend

**Native Codex remains experimental.** Keep the existing backend available and keep current default routing. Do not deprecate or delete the old transport based on catalog discovery and a failed startup. No backend has newly demonstrated the requested full Stage23 reliability gates.

The demonstrated blocker is native Windows sandbox provisioning from this execution boundary. Any separately authorized continuation should first establish a supported native launcher/sandbox and native sign-in outside role context, then obtain three fresh artifact-producing smoke runs before adding roles. Do not extract desktop credentials, build a proxy, broaden role host access, or substitute Astra to resolve it. This assessment does not perform that continuation.

## N. Recommended role routing

**No new production routing recommendation:** successful trials were a prerequisite. The requested future validation route remains exact `gpt-6.1-sol` for Implementer, independent Tester, Reviewer and Architect, with each phase gated in order. Cheaper task-size routing, Reviewer value and Architect inclusion remain unmeasured. This attempt ends after assessment and cleanup.
