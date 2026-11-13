---
{
  "title": "Execution and verification",
  "summary": "Run process, sandbox and project checks with honest evidence.",
  "status": "current",
  "related_files": [
    "agent_system/execution.py",
    "examples/native_smoke.py",
    "project_tooling/steam/verify.py",
    "examples/sandbox_probe.py",
    "tests/test_support.py",
    "tests/test_sandbox.py"
  ]
}
---

# Execution and verification

`agent_system/execution.py` constructs native worker commands for both vendors and
captures exit, timeout and process-group shutdown. Both launchers start the worker
from an empty environment plus `WORKER_ENV`.

- `command` launches Codex with a named permission profile.
- `claude_command` launches headless Claude Code inside `claude_fence`, an outer
  bubblewrap mount namespace around the whole process: read-only system, empty
  `$HOME` except login state and binary, read-only workspace with only the writable
  subtrees bound read-write, private `/tmp`, no `/mnt`, `/run/WSL` or `/run/user`,
  own PID namespace. Inside it, `claude_settings` turns on Claude's Bash sandbox
  (fail closed, no unsandboxed retry, no network) and `--restricted`, `dontAsk` and
  permission rules bound the file tools, which run outside that sandbox.
- Call `claude_prepare(workspace)` before the acceptance baseline. It creates the
  empty placeholders Claude's sandbox mounts over in a read-only working directory;
  `claude_command` refuses to launch without them. It requires Linux/WSL for
restricted execution; a Windows unit-test run does not establish Linux isolation.
Use installed native authentication; never copy credentials into role inputs.

For strict runs, verify denied private reads, forbidden write-opens and required
network restrictions on the actual installed runtime with the shared probe:

```text
python3 -B examples/sandbox_probe.py codex  /fresh/evidence/dir
python3 -B examples/sandbox_probe.py claude /fresh/evidence/dir
python3 -B examples/sandbox_probe.py codex  /fresh/evidence/dir --negative-control
```

It plants random canaries, runs one deterministic script through the worker's own
shell (and through `codex sandbox` for Codex), asks the worker to attempt the escapes
that bypass the shell, and judges only oracles: canary tokens absent from output,
protected bytes unchanged, changes confined to `tests/`, attempts visible in the
tool-call stream, and positive controls met. The worker's own report is never used.
Exit 0 is PASS, 1 FAIL, 2 INCONCLUSIVE. `--negative-control` exposes the canaries and
must FAIL; run it after a version change to show the probe still detects breaches.
Claude Code on Linux/WSL needs `bubblewrap` and `socat`; without them it refuses
to start, which is the intended fail-closed behavior. Claude's own safety classifier
may interrupt a probe command; that run is INCONCLUSIVE and should be repeated.
`STAGE34_SANDBOX_VERIFICATION_REPORT.md` records the demonstrated versions, findings
and limits. Configure only the explicit
public input files and required writable subtrees. Hash equality detects drift;
permission enforcement provides the boundary.

The retained `project_tooling/steam/verify.py` provisions and verifies the Steam
project in a disposable export with PostgreSQL. Follow its existing lifecycle and
record actual results. Package provisioning access and candidate-check access are
separate. Persistent services require explicit project-owned start/stop handling.

For this support workspace:

```text
python -B -m pytest tests -q -p no:cacheprovider
python scripts/docs.py check
```

Choose checks proportional to changed behavior. Linux process tests may skip on
Windows; report the skips and do not call them demonstrated shutdown guarantees.
The standalone `examples/native_smoke.py` runs separately inspected steps against
a fresh evidence directory; it is not an ordinary unit test or a run-all command.
