---
name: task-closeout
description: Prepare a completed project task for user handoff with actual verification evidence and remaining actions.
---

Use `docs/templates/closeout.md`, scaled to the task. Inspect the complete final
scope and distinguish existing user edits from this task. State actual check
results, skips, limitations and related documentation updates. For strict work,
include the authoritative acceptance decision and evidence location.

The user publishes Git changes personally. Supply exact commands only when the
actual repository, branch and intended changes are known. Do not push, merge a PR,
write repository contents through an API, or trigger equivalent publication unless
separately explicitly authorized. Supply commit and push commands for the user's
review instead; never invent publication commands for a state you have not checked.
