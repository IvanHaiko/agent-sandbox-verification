# Native/custom capability inventory

Inspected on 2026-10-09. Executed Linux CLI: 0.160.1. Desktop Windows CLI:
0.162.0-alpha.2. The comparison intentionally uses the same existing Linux CLI for both.
Saved CLI help and feature inventory are installed-version evidence, distinct from current docs.

The official [Subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
describes native delegation, agent-specific configuration, and inherited parent sandbox
and approval controls, including possible read-only agent configuration. Native contexts
do not by themselves establish separate filesystems. Separate Git copies/worktrees are
normal native-workflow tools. Effective runtime permissions must be checked, especially
where a parent override can take precedence. Current documentation is not proof that
every feature behaves identically in the older installed CLI.

| Concern | Native configuration A | Existing framework B |
|---|---|---|
| Conversation/context | Native parent and role subagents; fresh role context requested | Separate ephemeral CLI exec per role; no inherited history |
| Files | Independent Git working copies under A root | Private role repositories; exact selected bundles |
| Tools/permissions | Native parent permission profile, native reviewer config; inherited controls | Native per-role permission profiles plus Controller preflight probes |
| Blind tests | Tester first; no candidate yet; public-only tester copy; independent suite frozen by parent | Public-only tester bundle; denied cross-role paths; Controller validation and freeze |
| Integrity/reproduction | Native Git diff, hashes and preserved artifacts; external evaluator checks | Existing snapshot/hash checks, structural artifact validation, Controller decision |
| Functional oracle | Shared external evaluator; independent tester | Shared external evaluator; independent tester and deterministic Controller acceptance |

Formal test independence, task-specific frozen acceptance, scope validation and a
deterministic pass/fail policy are workflow choices rather than automatic consequences
of spawning agents. This does not prove those choices require a generic custom framework.

The Stage 25 assessment retains a successful but intervened retry. Stage 26 retains
useful candidate work and a failed independent artifact gate. Its existing post-experiment
collection-order correction is retained: rejected outputs must be archived before cleanup.
Neither historical task patch is incorporated into the current pinned source.

The task's lexical behavior follows the bounded subset stated in the frozen contract;
PostgreSQL documents quoted strings, dollar tags and nested comments in its
[lexical syntax reference](https://www.postgresql.org/docs/current/sql-syntax-lexical.html).
This benchmark deliberately requires a reusable splitter interface and individual statement
execution; sending a whole file to PostgreSQL would not satisfy that interface contract.
