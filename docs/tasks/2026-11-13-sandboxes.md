# Restricted workers for Codex and Claude Code — 13 November 2026

Result: both vendors now have a strict restricted-worker path on Linux/WSL2, verified
live with the same probe. Codex 0.160.1 and Claude Code 2.1.323 both PASS, and both
negative controls FAIL as required. Full account: `STAGE34_SANDBOX_VERIFICATION_REPORT.md`;
evidence: `docs/stage34-verification/` (18 recorded runs, all kept, listed in `summary.json`).

Changed behavior:
- `agent_system/execution.py`:
  - `worker_env` allow-list for both vendors' launches;
  - `claude_settings`, `claude_fence`, `claude_prepare` and `claude_command` added;
  - `command` gained `model`;
  - writable subtrees are rejected when absolute on any host, or when a link or file.

  Generic `process()` keeps its old environment filter, because project tooling relies on
  variables such as `GIT_OPTIONAL_LOCKS`.
- `examples/sandbox_probe.py` (new): the shared live verification and its negative control.
- Tests: new `tests/test_sandbox.py`; `tests/test_support.py` unchanged apart from the earlier
  environment test.
- Docs: README, `docs/guides/execution.md`, `docs/guides/workflow.md`, AGENTS.md and
  CLAUDE.md; the Stage 34 link was added to the docs index.

Verification:
- `python -B -m pytest tests -q -p no:cacheprovider`: 52 passed, 4 skipped on Windows (POSIX
  process checks and host symlink tests).
- `python scripts/docs.py check`: OK.
- Live runs in WSL2 are listed in `summary.json`. After the final runs, the only change to
  the probe was renaming the Codex patch counter from `applied` to `executed`; the judging
  logic is unchanged.
- Regression after the `env -i` launch prefix, recorded in
  `docs/stage34-verification/regression/`:
  - `examples/native_smoke.py`: all 8 steps passed, and the deliberate fault was rejected.
  - `project_tooling/steam/verify.py`: run on the Stage 31 commit `68edb39` from the Stage 31
    bundle; 182 passed, ruff clean, TCP denied, PostgreSQL stopped, workspaces removed.

Independent review: a separate read-only reviewer found real gaps before the final runs:
- `/mnt/c` and WSL interop were reachable;
- the environment filter was a deny-list;
- probe results could be forged;
- step matching was vacuous;
- Glob/Grep successes leaked file names;
- symlink writes were not probed.

All were fixed and are covered by the probe.

Environment setup done for this task: Claude Code 2.1.323 installed in WSL via the official
installer (script read before running; it remains at `~/.cache/claude-install/install.sh`).
The user installed `socat` and logged in. Live evidence also remains in WSL at
`~/sandbox-evidence/`, copied into the repository. The regression runs left
`~/stage34-regression/` in WSL: the Steam bundle clone and the 94 MB runtime archive.

Remaining risks and limits are in the Stage 34 report. In short:
- WSL2 only;
- Claude's own safety classifier can interrupt a probe run, which then counts as INCONCLUSIVE;
- the placeholder list is version-specific and fails closed when it changes;
- the Claude process itself can read `~/.claude`;
- `setsid` escapes process-group shutdown.

No Git publication; this workspace has no root Git metadata.
