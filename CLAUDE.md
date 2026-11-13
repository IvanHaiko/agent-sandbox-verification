@AGENTS.md

## Claude Code

`AGENTS.md` above is the shared source of project rules for Codex and Claude Code.
Edit rules there, not here.

- Project skills are discovered from `.claude/skills/`. Those files are generated
  copies of `.agents/skills/`: edit the source, run `python scripts/docs.py build`,
  and `python scripts/docs.py check` fails if a copy drifts.
- Model tiers use the Claude column of the AGENTS.md table, passed as the subagent
  `model` argument (`haiku`, `sonnet`, `opus`).
- Strict restricted workers exist for both vendors on Linux/WSL2: `command` (Codex)
  and `claude_command` (Claude Code, after `claude_prepare`). Verify them with
  `examples/sandbox_probe.py` and its negative control on the installed versions;
  see `STAGE34_SANDBOX_VERIFICATION_REPORT.md`. Subagent worktrees are separate
  contexts, not filesystem isolation.
