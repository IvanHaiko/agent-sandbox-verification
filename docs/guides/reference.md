---
{
  "title": "Support package reference",
  "summary": "Execution and acceptance API, trust model, failure handling, example and rollback.",
  "status": "current",
  "related_files": [
    "agent_system/*.py",
    "examples/native_smoke.py",
    "project_tooling/steam/verify.py",
    "pyproject.toml"
  ]
}
---

# Support package reference

Python 3.11+ is required. The installed package has **no runtime dependencies**.
Development checks need pytest (`python -m pip install -e '.[dev]'`). Strict
execution requires Linux/WSL2, the vendor CLI installed and logged in, and for
Claude Code also `bubblewrap` and `socat`.

## Execution: `agent_system.execution`

| Function | Purpose |
| --- | --- |
| `process(argv, workspace, prompt=, timeout=)` | Run one owned process group; capture real exit, timeout and process-group shutdown. |
| `worker_env(**extra)` | `env -i` prefix with the `WORKER_ENV` allow-list; used by every worker launch. |
| `permissions`, `sandbox`, `command` | Codex: named permission profile, model-free sandboxed command, restricted `codex exec`. |
| `claude_prepare(workspace)` | Create the empty placeholders Claude's sandbox mounts over; call before the baseline. |
| `claude_settings`, `claude_fence`, `claude_command` | Claude Code: session settings, outer bubblewrap fence, restricted headless launch. |

The process helper remains because native managed cancellation has not shown the
same shutdown guarantee. A descendant that calls `setsid` escapes the group.
Persistent project services need explicit project-owned start/stop handling.

Choose model and effort through native CLI arguments (`model=` on both launchers,
or `-c model_reasoning_effort=...` for Codex). Python holds no role mapping or
model policy; `AGENTS.md` describes the adaptive choice.

## Acceptance: `agent_system.acceptance`

`workspace`, `snapshot`, `freeze`, `accept`, `preserve` and `cleanup`. Workspaces
receive explicit `{relative_path: bytes}` inputs, never recursive copies of another
role's directory. Strict exports have no `.git` object database. `snapshot`
includes hidden, added, deleted and untracked regular files and rejects symlinks,
junctions and hardlinks.

```python
from agent_system.acceptance import accept, freeze, snapshot

baseline = snapshot(candidate_workspace)  # before implementation (after claude_prepare)
frozen_hashes = freeze(public_tests_and_contract, new_frozen_version_directory)
# The parent runs the separate Implementer and all required checks.
decision = accept(
    candidate_workspace, baseline,
    allowed=["src/main.py", "src/helper.py"],
    required=["src/main.py", "src/helper.py"],
    processes={"implementer": implementer_outcome, "reviewer": reviewer_outcome},
    checks={"independent": frozen_test_outcome, "regressions": regression_outcome},
    frozen_root=new_frozen_version_directory, frozen_hashes=frozen_hashes,
    review={"accepted": True, "blockers": []},  # actual inspected review
)
```

`accept` executes nothing. Supply every required result from actual execution,
never invented successes or omitted failing checks. Each outcome needs an integer
`exit_code`, boolean `timed_out` and `owned_process_group_ended`. It blocks
nonzero or incomplete execution, missing final files, out-of-scope changes, frozen
drift, failed checks, reviewed blockers and unresolved environment errors. It
validates the **complete final workspace**; an unchanged primary file with an
authorized helper-only repair is valid. Failure groups: process/environment,
artifact/scope, behavior/review. The review and frozen checks are optional
arguments: pass them whenever the task's risk requires them.

## Failure, repair and cleanup

Before cleaning a role workspace, call
`preserve(workspace, fresh_archive_path, {"workspace": str(workspace), ...outcome})`.
It stores regular file bytes, process diagnostics and link metadata without
following links (`files/`, `outcome.json`, `links.json`). Archives are exclusive:
a later attempt cannot overwrite a failure. `cleanup(workspace, preserved=archive)`
checks ownership, archive identity and preserved bytes before removing the
workspace. Failed preservation leaves the workspace available for diagnosis.

Frozen tests never change during repairs. If an expectation is wrong, keep the
failed result, identify the oracle disagreement and require explicit adjudication.
A reviewed superseding version is a new directory and receipt. Never relabel the
old failure or alter correct code to satisfy a known incorrect expectation.

## Trust model

The parent and deterministic helpers are trusted. A sandbox constrains worker
tools, not a malicious parent or unrelated host processes. Hashes detect drift;
they do not replace permission enforcement. Separate chats and worktrees are not
isolation. Strict Windows child boundaries have not been demonstrated. Files a
worker writes under its writable subtree (for example `conftest.py`) are executed
downstream only inside a restricted run.

## Examples

`examples/sandbox_probe.py` verifies a vendor's boundary; see the execution guide.
`examples/native_smoke.py` is a clamp fixture exercising the high-risk path with
Codex, one step at a time, each inspected before the next:

```bash
for step in small tester implementer evaluate fault repair reviewer cleanup; do
  python3 -B examples/native_smoke.py /absolute/fresh/evidence "$step" || break
done
```

There is no `run-all`, automatic repair loop or generalized task protocol.

`project_tooling/steam/verify.py` is the **Steam-specific** recipe. It exports a
fixed commit read-only, installs that project's requirements, runs the whole suite
and Ruff against a disposable PostgreSQL on an owned UNIX socket in a private
network namespace, preserves outputs and stops the server. It never loads the
original `.env` or touches the original Git index or worktree registry.

## Rollback to the old Controller

Stage 25–29 material is historical and not imported at runtime. For explicit
rollback, verify `docs/stage30-verification/source-rollback.zip` against
`rollback.json` and extract it into a **separate empty checkout**. Never mix old and
new runtime modules or silently fall back to the old Controller.
