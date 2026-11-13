# Claude Code compatibility — 13 November 2026

Result: the workflow now runs from Claude Code as well as Codex. `CLAUDE.md`
imports `AGENTS.md`, so both agents read one rule source. `scripts/docs.py build`
writes exact copies of `.agents/skills/<name>/` into `.claude/skills/<name>/`,
where Claude Code discovers project skills, and `check` fails on drift. Only
mirrored skill directories are managed; other `.claude/skills/` entries are left
alone. AGENTS.md gives Claude Code model tiers (`haiku`, `sonnet`, `opus`) beside
the Codex ones. Worker launches in `agent_system.execution` also drop
`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_BASE_URL` and
`CLAUDE_CODE_OAUTH_TOKEN`.

Changed: CLAUDE.md (new), AGENTS.md, README.md, scripts/docs.py,
agent_system/execution.py, tests/test_docs.py, tests/test_support.py,
docs/guides/{adoption,documentation,workflow}.md, docs/README.md (regenerated),
.claude/skills/*/SKILL.md (generated).

Verification: `python -B -m pytest tests -q -p no:cacheprovider` reported 28 passed
and 3 skipped on Windows (existing POSIX-only process checks). Before the first
build, `docs.py check` exited 2 and named all four missing copies; after build it
passed and `cmp` matched every copy byte for byte. Path lookup maps CLAUDE.md and
`.claude/skills/` files to guides.

Not verified: live discovery by a fresh Claude Code session. The headless
`claude -p` probe failed because its OAuth session had expired. Open a new session
in this folder and confirm the four project skills are listed.

Unchanged by design: the strict path still launches the Codex CLI; no Claude Code
permission-profile equivalent was built or probed. The `.codex-owned` marker and
`codex-role-` prefix stay, because `cleanup` matches them on existing workspaces.
