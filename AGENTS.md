# Project working agreements

Read `docs/README.md` first, then only the guides relevant to the task. Historical
stage reports are evidence of particular runs, not current operating instructions.

These rules apply to Codex and Claude Code alike; `CLAUDE.md` imports this file
and adds only Claude-specific notes.

For code or tooling changes, use the project `change-verification` skill. For
behavior or workflow documentation changes, use `docs-sync`. Use `task-closeout`
when handing completed work back. Their instructions live in `.agents/skills/`;
`.claude/skills/` holds generated copies rebuilt by `python scripts/docs.py build`.
For substantial work, use `docs/templates/task.md` as a brief; small edits need
only a concise statement of scope and verification.

Keep orchestration native. The installed package provides execution boundaries
and acceptance helpers, not a Controller or role scheduler. Choose small, medium,
or high-risk handling from `docs/guides/workflow.md`. Separate chats and worktrees
do not enforce blind testing or read-only review. Strict execution requires the
demonstrated Linux/WSL path and actual permission probes, for Codex or Claude Code
workers (`examples/sandbox_probe.py`).

Update documentation related to changed behavior. Find it with
`python scripts/docs.py for PATH [PATH ...]`. Regenerate the index with
`python scripts/docs.py build`, then run `python scripts/docs.py check`.
Preserve historical reports, frozen tests, receipts and failed evidence.

The user performs Git publication personally. Never push branches or tags, merge
PRs, write repository contents through an API, or trigger equivalent publication
without a separate explicit instruction authorizing that publication. Provide
the applicable commands at handoff. General implementation requests do not
authorize publication. The repository is published at
https://github.com/IvanHaiko/agent-sandbox-verification. Do not change nested
repositories under ignored scratch directories as incidental setup.

## Connecting another repository

When asked to connect this workflow to another project, follow
`docs/guides/adoption.md`. Inspect and adapt the target's existing instructions,
checks and documentation; do not copy this workspace's project-specific claims.
Keep target changes local and preserve existing user work.

Ready-to-use prompt in the target project's chat:

> Подключи к этому репозиторию мой процесс разработки из
> C:/Users/4ivan/codex-multi-agent. Следуй docs/guides/adoption.md из этого
> комплекта: адаптируй AGENTS.md, скиллы, документацию и проверки под этот проект,
> сохрани существующие правила и мои изменения, проверь подключение.
> Модели выбирай по таблице из AGENTS.md комплекта для того агента, в котором работаешь.
> Публикацию в Git выполню самостоятельно.

After adoption, ordinary requests can simply state the desired change and
acceptance criteria; project instructions supply the workflow automatically.

## Adaptive agents and models

The user authorizes automatic subagent delegation and model selection within the
requested task. Assess complexity, ambiguity, impact and separable work before
choosing the smallest useful team. Briefly state the choice and proceed without
asking the user to select models or agent counts. Respect explicit user overrides,
actual available models, concurrency limits and higher-priority execution rules.

| Task | Default team, including coordinator | Codex models | Claude Code models |
| --- | --- | --- | --- |
| Small, clear, reversible | Coordinator alone; optionally one bounded worker when a different model is useful. | Prefer GPT-6.1 Terra (`gpt-6.1-terra`) for bounded worker tasks, medium effort. | `haiku` for bounded worker tasks. |
| Medium, multiple files or meaningful behavior | Coordinator plus implementer; add independent review when useful, usually 2-3 agents total. | GPT-6.1 Sol (`gpt-6.1-sol`) for implementation; Terra for bounded checks/docs, Sol for substantive review. | `sonnet` for implementation and substantive review; `haiku` for bounded checks/docs. |
| Complex, ambiguous or high impact | Coordinator plus focused implementation, testing and review roles, usually 3-4 concurrent agents total; sequence roles if needed. | Sol at high effort for engineering; GPT-6 Astra (`gpt-6-astra`) for difficult design, diagnosis or consequential review. | `sonnet` at high effort for engineering; `opus` for difficult design, diagnosis or consequential review. |

Use the column for the agent actually running the task. Claude Code names are the
subagent `model` aliases, so they follow the current model family.

These are adaptive defaults, not quotas or proven quality rankings. Raise effort
or use a stronger model when evidence shows unresolved ambiguity or failures;
add agents only for useful parallel work or independent verification. Do not run
successful unrelated workers again or inflate a small edit into a fixed pipeline.
For strict high-risk work retain the target's verified public-input Tester,
frozen tests, restricted execution and read-only review procedure. A model choice
or extra chat does not establish filesystem isolation.

The active chat remains coordinator; worker models are selected through native
model arguments when supported. Do not ask the user to switch the parent model
for each task. Give model-specific workers fresh, self-contained task context
when required by the tool (for example Codex fork_turns=none, or a fresh rather
than forked Claude Code subagent), explicit file ownership,
acceptance criteria and verification commands. Avoid concurrent edits to the same
files. Review actual output before integrating it.

If delegation or model selection is unavailable, use the available execution
path and report the limitation; never claim unperformed routing or a model that
was not selected. This authorization covers subagents within the current task,
not creating user-owned chats, contacting others, changing global model settings,
remote publication or recurring automations.
