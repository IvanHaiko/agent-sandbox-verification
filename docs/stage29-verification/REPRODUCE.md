# Stage 29 evidence and reproduction

Executed 9 October 2026. These are architecture probes, not a repeat of the Steam engineering benchmarks. All new files are Stage 29 reports/evidence. The original project and active framework were read only.

## Evidence map

| Question | Evidence |
|---|---|
| What source exists, and how large is it? | `source-inventory.json`: hashes, imports, definitions, physical and nonblank/noncomment lines |
| Were previous ZIPs actually inspected? | `previous-archives-audit.json`, `stage27-selected-evidence.json`, `stage28-selected-evidence.json` |
| Does an ordinary native child have private role boundaries? | `native-agent-probe.json`: fresh `fork_turns=none` child, actual canary reads and O_WRONLY open |
| What does configured native enforcement do? | `experiment-a.json`, `experiment-a-native-explicit.json` |
| How are invalid outputs, scope changes and process failures handled? | `experiment-b.json`, `b-controller-*/assessment.json`, `b-controller-*/controller-decision.json` |
| Can independent tests be wrong? | `b-oracle.json`, `c-reviewer-result.json`; Stage 28 archived evidence supplies the nontrivial real-world example |
| Can a small hybrid path run? | `c-contract.md`, `c-tester-input.md`, `c-*-execution.json`, `c-freeze.json`, `c-frozen-design.json`, `c-frozen-acceptance.py`, `c-candidate.py.txt`, `c-acceptance.json`, `c-review-integrity.json` |
| Existing regression checks | `framework-regression.txt`, `framework-regression.xml` |
| Source/original preservation and resource cleanup | `workspace-integrity.json`, `original-integrity.json`, `cleanup.json`, `final-summary.json` |

The two original ZIPs matched their recorded SHA-256 and passed all-member CRC checks. Selected archived decisions, reviews, evaluation and integrity records were parsed without extraction or model reruns. This is not a claim to have independently rerun their engineering acceptance suites or checked every prior member against its internal manifest.

## Requirements

Use the current unchanged source checkout under WSL Ubuntu, Python 3.11+, Git, installed Linux Codex and native login. Observed versions: Linux Codex 0.160.1, Python 3.14.4, Git 2.53.0, jsonschema 4.19.2, pytest 9.0.2. Desktop Codex is a different executable, 0.162.0-alpha.2. Nothing was installed for Stage 29. Native `multi_agent` is enabled; the current runner deliberately disables nested subagents for its restricted role sessions.

Set `PYTHONDONTWRITEBYTECODE=1`; use `python3 -B` and disable pytest's cache. The scripts refer to this checkout and the original `/mnt/c/Users/4ivan/steam-etl` for read-only fingerprints. Do not invoke the historical Steam runtime/control/resume modules: some execute work at import time.

## Deterministic probes

Use a fresh evidence directory by copying the two probe scripts there and adjusting `ROOT` if it is outside `docs/<directory>`. Do not overwrite the sealed Stage 29 results. The scripts are evidence-only; they are not a supported product API.

From the unchanged source root in WSL:

```bash
python3 -B docs/<fresh-directory>/probes.py original-before
python3 -B docs/<fresh-directory>/probes.py a
python3 -B docs/<fresh-directory>/probes.py a-native-broad
python3 -B docs/<fresh-directory>/probes.py b
```

Probe A creates existing canaries in private sibling Git repositories. It opens descriptors only; it never truncates or writes the review canary. The first attempted shorthand `sandbox_mode="read-only"` sandbox command failed before executing the probe because this installed `codex sandbox` requires `--permission-profile`. That failure remains in `experiment-a.json`. The follow-up uses an explicit named native profile and retains a separate result. Broad read access permits sibling reads while denying writes; the minimal-read profile denies both sibling reads and review writes.

Probe B replaces **only the model process result** with deterministic mutations. Native sandbox preflight, current runner artifact admission, and current Controller failure closeout are real. The supplied native session metadata is explicitly synthetic. It does not measure how often models make those mistakes. The failure closeout injects a rejected receipt into the label Controller; it tests rejection/cleanup rather than label behavior. The clamp candidate bytes live in its disposable workspace, and the Controller's own prepared-target write is also disposable. Failure categories and artifact loss are observed, not model judgments. Actual exit-17 and timeout subprocesses separately exercise real process shutdown. The additional secondary-only repair is a narrow diagnostic within the scope scenario, not another engineering benchmark.

## Minimal workflow: model quota required

The native parent invoked these steps separately and chose their ordering. There is no `run-all`, new controller, role scheduler, repair engine, service or permanent framework component.

```bash
python3 -B docs/<fresh-directory>/probes.py c-tester
# Inspect receipt; freeze exists and Tester has ended before continuing.
python3 -B docs/<fresh-directory>/probes.py c-implementer
python3 -B docs/<fresh-directory>/probes.py c-evaluate
python3 -B docs/<fresh-directory>/probes.py c-reviewer
python3 -B docs/<fresh-directory>/probes.py cleanup
python3 -B docs/<fresh-directory>/probes.py original-after
```

There were exactly three restricted model invocations, using the unchanged runner's supported gpt-6.1-sol/medium route. No successful role was resampled. The parent used native conversation/tool execution to coordinate them, not the custom `run_workflow`. They are separate ephemeral native CLI role sessions, **not** built-in spawned children with individually configured permissions. The proof retains the existing runner/artifact helpers; it demonstrates that the custom Controller is unnecessary for this fixture, not that a production thin support layer has already been implemented or verified for dependency-heavy projects.

`c-evaluate` uses the frozen candidate/design in a read-only sandbox. It separately executes one deliberately wrong oracle expectation, `[5,0,3] -> 5`, against the correct result 3. That case never replaces a frozen independent test. The Reviewer receives both records and must adjudicate the disagreement. Frozen files stay unchanged.

The native desktop child canary probe is reproduced by spawning one fresh-context child, supplying only the four disposable paths and instructions to attempt reads and nontruncating write-open without escalation. The main chat's default child API has no per-child filesystem option. Do not substitute a new configured agent type and relabel its results as this default API.

## Integrity, cleanup and packaging

`inspect_evidence.py before/after` hashes pre-existing workspace regular files and records unchanged access-error markers for 65 inaccessible old scratch entries. It does not assert the bytes of inaccessible entries. Stage 29 output paths are excluded. Full before/after workspace manifests are retained locally but omitted from the compact ZIP; the source inventory and integrity delta suffice for delivery. Original project fingerprints cover HEAD, branch, raw index hash, staged/working diffs, tracked and nonignored untracked files, with Git optional locks disabled; ignored production data and credentials are not read.

Owned Linux workspaces are registered in `owned.json` and cleaned only through the existing `codex-role-*` ownership checks. Stage 29 pytest scratch and Windows canaries are removed after results are retained. Pre-existing scratch, caches and `.agent_runs` are untouched.

Setup observations retained transparently: Windows WSL discovery initially returned access denied and succeeded through the authorized WSL execution route; WSL has no `rg`, so an initial features pipeline ended with a broken-pipe diagnostic and was replaced with direct captured output. The first Windows inventory attempt stopped on an inaccessible historical scratch entry, then the inventory recorded those access errors explicitly. None was a model/provider failure or a changed experiment outcome.

The compact archive contains both reports, relevant Stage 29 JSON/text/XML evidence and probe sources. It excludes previous ZIPs, copied repositories, caches, scratch, credentials and redundant full workspace manifests. `delivery-receipt.json` and `evidence-manifest.json` verify its digest, member hashes and CRCs.
