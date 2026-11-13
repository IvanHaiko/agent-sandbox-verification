# Task cards

One markdown file per task, from `docs/TASK_TEMPLATE.md`, named
`NNN-short-slug.md`.

These are tracked in git on purpose. They are the written trail a review and a
handoff run on, and for a repository someone will read as portfolio they show
how a decision was reached — which forks existed, what was chosen, what it cost.
If they ever become noise rather than evidence, one line in `.gitignore` retires
them; the template stays useful either way.

Cards are not a substitute for `PROGRESS.md`. The card is the record of one
task while it runs; `PROGRESS.md` is what a session leaves behind for the next
one. When a card is accepted, what survives it moves into `PROGRESS.md`,
`ARCHITECTURE.md` or `ROADMAP.md` — and only the parts that were confirmed.
