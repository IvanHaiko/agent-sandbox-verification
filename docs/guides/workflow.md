---
{
  "title": "Engineering workflow",
  "summary": "Choose task scope and small, medium or high-risk controls.",
  "status": "current",
  "related_files": [
    "agent_system/*.py",
    "examples/native_smoke.py",
    "AGENTS.md",
    "CLAUDE.md"
  ]
}
---

# Engineering workflow

The native parent chooses and coordinates work. `agent_system` supplies narrow
execution and acceptance functions; it has no scheduler or repair engine.
The [reference](reference.md) contains the detailed API and trust model.

| Risk | Default procedure | Repair budget |
| --- | --- | --- |
| Small | One session, scoped edit, relevant existing checks, final diff. | Reassess if scope or risk grows. |
| Medium | Explicit allowed paths, preserved baseline, project checks and complete final scope check. Independent review when useful. | One targeted repair, then reassess. |
| High | Restricted public-input Tester, frozen tests before candidate exposure, separate Implementer, direct checks, restricted read-only Reviewer, deterministic acceptance. | At most two targeted implementation repairs. |

A small change needs one native session and the project's relevant checks, for
example: "Update the footer spacing in `src/footer.css`. Run the existing stylesheet
check and show the diff. Keep the change confined to that file." Medium work states
exact permitted paths, preserves the baseline and checks the complete final scope;
default to one targeted repair, then escalate. High-risk work, run by the parent:

1. Create a private source-only Tester workspace with only the public contract,
   interfaces and selected public fixtures. Verify permission denials with canaries.
2. Run an independent restricted Tester. Collect executable tests and a concise
   coverage explanation; verify its exact output scope. Freeze the tests and
   contract as a fresh version outside every worker's writable paths.
3. Run a separate restricted Implementer on a preserved baseline with explicit file
   scope. Freezing precedes candidate creation or exposure.
4. Run the frozen tests and required project checks with source and frozen inputs
   read-only and only project scratch writable. Keep exits and output; verify final
   artifacts, exact scope and frozen hashes.
5. Give a read-only restricted Reviewer the contract, scoped baseline and candidate,
   diff, frozen tests and detailed results, including failures. Verify denied
   write-opens and unchanged hashes.
6. Call `accept` with every required outcome and the review. Its decision is final.

Budgets are operating defaults; an explicit task budget takes precedence. Small
reversible edits need no mandatory independent roles or new tests. Use the task
brief template for substantial work and the closeout template at handoff.

Strict execution is demonstrated on Linux/WSL2 with actual permission-denial probes
for both Codex and Claude Code restricted workers (Stage 34).
Separate contexts or worktrees do not enforce peer-read secrecy or read-only review.
Unsupported profiles fail closed. Do not infer current CLI behavior from a past report.
See the [reference](reference.md) for launch functions and acceptance inputs, and the
[acceptance guide](acceptance.md) for raw Git-index protection.

Projects own dependencies, services and check commands. The Steam verification
recipe is project-specific, not a generic workflow entry point. Preserve failures
before cleanup. Do not reinterpret failed historical decisions after later fixes.

## Automatic team and model choice

Apply the adaptive policy in the project AGENTS.md before execution. The user
states the outcome; the coordinator chooses models, effort and useful delegation.
Small work usually stays in one session; medium work may separate implementation
and review; complex/high-risk work separates testing, implementation and review
where justified. Codex defaults are Terra for bounded work, Sol for engineering and
Astra for difficult reasoning; Claude Code defaults are `haiku`, `sonnet` and
`opus` in the same roles. Choose against actual availability and task risk.
State the selected team briefly and use native worker model arguments; the parent
chat can remain unchanged. Report limitations honestly. Do not mistake extra
agents for the strict isolation guarantees described above.
