# Task card template

Copy to `tasks/NNN-short-slug.md` when a task starts. One file per task, not one
folder of six — this is a one-person project with agents, and the point being
borrowed is the **verifiable trail**, not the ceremony. A card that costs more to
keep than the task costs to do will stop being kept.

## Why the card exists

Between two agents only text passes. Everything the implementer understood but
did not write down dies at that boundary, and the next agent starts cold. The
card is that boundary made durable: the next participant works from a written
trail rather than from someone's memory of a conversation.

It also fixes a leak this project already had. When a review was briefed by
retelling the context by hand, the briefer's own hypothesis went along with it,
and the reviewer started inside someone else's map. With a card, the reviewer is
handed a section — not a retelling.

## Who reads what

| Section | Written by | Read by |
|---|---|---|
| Brief | lead (main thread) | everyone |
| Forks and decisions | lead, after Ivan chooses | everyone |
| Implementation | the implementing agent | **lead only, at acceptance** |
| Out-of-scope findings | whoever hits one | lead |
| Review | reviewer | lead, then implementer if returned |
| Acceptance | lead | — |

**The reviewer gets Brief + diff + the repository documents, and not the
Implementation section.** A reviewer who reads the author's account of what they
verified adopts it, and the second opinion stops being second. The plan is
context about the *problem* and is required; the report is context about the
*author's confidence* and is contamination.

## Status

`planned` → `in-progress` → `review` → (`changes-required` → `in-progress` → …)
→ `accepted`. Only the lead sets `accepted`, and only after a review that
returned **clean**. At most two returns; after that the decision goes to Ivan.

---

```markdown
# NNN — <short title>

status: planned
opened: YYYY-MM-DD
zone: ingestion | warehouse | orchestration | analytics

## Brief

What is being changed, and why now. One paragraph.

**Boundaries.** Which files and schemas are in scope; what is explicitly out.

**Done when.** Numbers or commands, never adjectives. "Coverage improved" is not
a done-criterion; "resolved ≥ 600 of 978 observed categories, reported by
`mart_identity_coverage`" is.

**Known risk.** What could go wrong quietly, so the reviewer knows where to dig.

## Forks and decisions

One entry per fork that was put to Ivan. Options considered, what was chosen,
what it costs. This is the section that stops the same argument being had twice
in three weeks.

## Implementation

Files changed. Commands run and their real output. Before/after numbers. **What
was deliberately not done, and why.** Not read by the reviewer — see above.

## Out-of-scope findings

Defects noticed while doing something else. **Not fixed here.** Each one gets a
reproduction — the query, the command, or the mutation that shows it — not a
one-line note. A finding recorded as a sentence has to be re-investigated from
scratch when someone picks it up; that has already happened once with the 27
redirected appids.

## Review

Verdict, findings ranked by severity, and the required **Beyond the brief**
section — what the reviewer found that nobody pointed them at. Empty is a
legitimate answer and a signal.

## Acceptance

What the lead accepted, and what moved to the backlog instead.
```

---

## Knowledge lifetime — what goes where

Borrowed rule, and the one worth borrowing most: **only confirmed knowledge
reaches the general documents.** A hypothesis lives in the task card until it is
verified.

| Kind | Home |
|---|---|
| A hypothesis, a suspicion, an unverified number | the task card |
| A measured fact, a decision with its reasoning | `ARCHITECTURE.md`, `PROGRESS.md` |
| Something to do later | `ROADMAP.md`, with a reproduction if it is a defect |
| A term worth remembering | `docs/GLOSSARY.md` |

This project has already paid for ignoring it: a defect list was carried into
`CLAUDE.md` from an older file without being checked, and two of its entries
turned out to be false — the subcommand was wired, the token was cached. Under
this rule they would have sat in a task card until someone ran the check.
