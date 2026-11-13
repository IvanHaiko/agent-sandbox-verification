---
{
  "title": "Evidence-based retrospective",
  "summary": "Review completed work and propose focused process improvements.",
  "status": "current",
  "related_files": [
    "docs/templates/retro.md",
    "docs/templates/closeout.md",
    ".agents/skills/workflow-retro/SKILL.md"
  ]
}
---

# Evidence-based retrospective

Run on request or after a meaningful batch of completed tasks. Start with actual
closeouts, execution results and failures from the chosen period. Historical stage
reports establish past outcomes, not current-week activity. With no new evidence,
report that limitation rather than manufacturing a trend.

Use the retro template. Group repeated friction by cause: environment setup,
missing context, unclear scope, implementation defect, disputed expectation or
verification gap. Link each finding to its evidence. Distinguish observations from
inferences and unknowns. Recommend a narrow change with an observable success
criterion; repeated failures may justify a script or skill, one-off quirks may not.

Useful measurements when available: completed tasks, repair rounds, verification
failures by cause, time to usable context and post-delivery defects. Record their
scope and source. Do not estimate token or dollar savings from file counts or LOC.

A retrospective produces a local report and proposed actions. Publication,
messages to other people, production access and recurring scheduling require the
corresponding user authorization. Favor maintaining the per-task docs-sync process
over a redundant nightly documentation agent. Test a recurring prompt manually
before scheduling it; notify on actionable findings, not unchanged state.
