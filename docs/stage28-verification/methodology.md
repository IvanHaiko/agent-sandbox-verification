# Stage 28 method and previous evidence

Inspected Stage 25, 26 and 27 assessments, Stage 27 frozen experiment, closeout,
delivery receipt/audit and integrity records, current README and active artifact,
Controller, semantic-role, native launcher and test-environment source. Stage 27's
ZIP matches recorded SHA-256 5f2f1512c583a11d4e44b8a5768f10b63aafb1945f083fa556f1f445d2d56efa;
137 members pass ZIP CRC verification. Stage 25's atomic Twitch-hour replacement,
Stage 26's Steam Store outcome refactor, and Stage 27's SQL splitter are excluded.

The original custom framework is a small native-WSL artifact workflow, not the
older archived model transport. It uses fresh ephemeral CLI sessions, role-specific
repositories, native permission profiles, snapshots, selected bundles, frozen
independent tests, deterministic acceptance and optional read-only semantic review.
Neither active framework code nor installed CLI configuration is changed here.

Real task evidence: committed transform_igdb_search_results uses
raw_data.get('data', []), treating missing data as success; nested collections are
used without consistent validation. upsert_igdb_game and upsert_twitch_category
unconditionally set updated_at on conflict. load_igdb_file already has a transaction
boundary: preserving and testing that boundary is part of the task, not a claim
that the baseline commits partially. The new capability is stricter validation and
persisted-value-preserving replay through these existing interacting components.

Improvements feasible without a framework redesign:

- Apply Stage 27's owned-scratch cleanup boundary before strict cleanup from the start.
- Give both reviewers original/candidate source, patch, contract, rubric, frozen
  independent design/harness and own independent result. Keep held-out evidence private.
- Record common provisioning, per-configuration workflow start/end, deterministic
  evaluation windows and later cleanup separately; retain native timing provenance.
- Preserve rejected test bytes and every failed result; no silent resampling.
- Freeze three behavioral mutations and demonstrate each against the held-out suite.
- Probe actual native parent read permissions and actual reviewer write permissions.
- Do not compare A aggregate JSON usage with B launcher text counters as cost.

Shared infrastructure limitation: both configurations retain the existing
RoleTestEnvironment and disposable PostgreSQL provisioning. These tools execute
predefined checks, not role delegation, test design or implementation. Consequently
the comparison can assess role orchestration and artifact management, but cannot
establish that all custom runtime support is unnecessary. Removing the facility
would change the architecture and add infrastructure contrary to this request.

Configuration A uses one native CLI Orchestrator plus three native subagents,
with fresh contexts requested, Tester first and native Reviewer configuration.
Configuration B uses deterministic coordinator sequencing plus fresh Implementer,
Tester and Reviewer CLI invocations. B removes the Implementer workspace before
blind design and freezes after structural validation. Different counts/order are
natural architectural differences. Both testers receive only the common contract,
public interfaces, unchanged fixture/schema and identical design schema/categories.
Neither receives the external suite or another candidate's material.

The allowed two repair cycles are for candidate defects reported by frozen
independent tests or concrete reviewer blockers. Within-invocation Implementer
debugging is development, not a post-handoff candidate repair. Held-out acceptance
is final evaluation, with no tuning afterward. Environment corrections are separate.

Runtime: installed Linux Codex 0.160.1, gpt-6.1-sol/medium for corresponding roles,
Python 3.14.4, PostgreSQL 18.6 and pinned committed requirements. Native help/features
and installed dependency versions are archived. Current official documentation at
https://learn.chatgpt.com/docs/agent-configuration/subagents was fetched on 2026-10-09:
native subagents have separate contexts, while filesystem/approval permissions
inherit from the parent unless configuration changes them. Installed probes take
precedence over assumptions from newer documentation.

The initial held-out suite had a missing closing bracket. Its frozen bytes and
failed baseline collection are preserved. Before any candidate existed, only that
bracket was fixed, the baseline rerun and a correction receipt/effective seal written.
No assertion or requirement changed. Both candidates use the identical corrected
suite. This is a coordinator evaluator defect, not candidate or architecture failure.

Interpretation: one trial per configuration, one fixed order, shared evaluator and
test facility, no statistical superiority claims. Quality uses behavior, meaningful
failure coverage, three distinct mutation detections, code judgment and workflow
reliability. More tests or controls alone never establishes better engineering.
