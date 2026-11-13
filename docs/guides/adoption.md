---
{
  "title": "Adopt the workflow in another repository",
  "summary": "Connect project instructions and skills with target-specific checks.",
  "status": "current",
  "related_files": ["AGENTS.md", "CLAUDE.md", "docs/guides/adoption.md", ".agents/skills/*/SKILL.md"]
}
---

# Adopt the workflow in another repository

Run adoption from a chat opened on the target project, with this support workspace
available for reads. The user's request to connect the workflow authorizes local
adaptation, not remote publication or recurring automations.

1. Read the target's existing AGENTS files, README, build/dependency files, CI and
   documentation entry point. Establish its actual stack and check commands.
   Inspect existing changes without overwriting or staging them. Follow any
   applicable protected-checkout/index procedure.
2. Merge a short workflow section into the target AGENTS.md. Preserve its own
   rules. Include its documentation entry point, verification commands, risk-based
   handling, related-document updates, handoff and the user's publication policy.
   For Claude Code, the target CLAUDE.md must import it: create one containing
   `@AGENTS.md`, or add that line to an existing CLAUDE.md without dropping its rules.
   Keep shared rules in AGENTS.md so both agents read one source.
3. Adapt the four skills under `.agents/skills/` to target paths and conventions.
   For Claude Code, place identical copies under `.claude/skills/`: through the
   target's adopted `scripts/docs.py build`, or by copying and noting the source.
   Inspect collisions before editing existing skills. Remove support-package-only
   commands and the assertion that the project has no Git metadata. Do not require
   Linux isolation for ordinary work; retain it only when strict guarantees matter.
4. Reuse the target's documentation structure. Add a small current-guide index and
   task/closeout/retro templates where useful. If adopting `scripts/docs.py`, adapt
   its history section, metadata mappings and test fixtures for the target before
   generating the index. Never copy our STAGE links as target-project history.
   Do not overwrite an existing docs README or docs.py without inspecting it.
5. Adopt the adaptive agents/models policy from the source AGENTS.md. The user
   delegates team size and worker model selection to the coordinator: Terra /
   `haiku` for bounded work, Sol / `sonnet` for substantial engineering, Astra /
   `opus` for difficult reasoning or consequential review (Codex / Claude Code). Adapt to available tools and concurrency limits.
   Preserve explicit user overrides and actual isolation requirements. Routine
   tasks should not require manual model switching or repeated delegation approval.
6. Validate changed skills, documentation links and the generated index if adopted.
   Exercise path lookup against a real target source file. Run relevant existing
   checks for any executable changes. Inspect final scope and report actual
   outcomes, missing prerequisites and commands the user can run next.

Keep the adoption small. The `agent_system` Python package is optional for strict
boundary/acceptance use; ordinary projects need no new runtime dependency. Avoid
copying execution histories, verification fixtures, secrets or environment files.
Do not initialize Git, replace CI, add a scheduler or publish changes incidentally.

Record the source workspace and adoption date in the target's workflow guide.
Later updates should compare the common procedure with local adaptations, not
overwrite them wholesale. There is currently no packaged installer or automatic
cross-repository updater.

One-time prompt:

> Подключи мой процесс разработки из C:/Users/4ivan/codex-multi-agent к этому
> проекту по docs/guides/adoption.md. Адаптируй правила, скиллы и проверки,
> сохрани мои изменения. Публикацию выполню самостоятельно.

Everyday prompt after adoption:

> Исправь [проблему]. Ожидаемый результат: [критерии готовности].

Project instructions supply verification, documentation updates and handoff.
The existing retrospective automation belongs to the support chat; it does not
automatically monitor newly connected repositories.
