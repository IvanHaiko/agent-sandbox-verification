# Frozen Stage 27 task: PostgreSQL-aware migration statement boundaries

Both configurations start from Steam ETL commit `0653617666399590c853c39f08e8cf97c9eca45c`.
The original dirty checkout is excluded. Neither Stage 25 nor Stage 26 patches are included.

Implement `src.sql_statements.split_sql_statements(sql: str) -> list[str]`, and integrate it
into `src.migrations.run_migrations(migrations_dir: Path | None = None) -> None`.
The current `sql.split(';')` corrupts SQL literals, comments and function bodies.

1. Split only on semicolons outside SQL quoted/comment regions. Return ordered original
   fragments with outer whitespace stripped and the separating semicolon excluded.
   Preserve internal text and comments. Ignore empty and comment-only fragments.
   A final statement without a semicolon is valid. Input is not mutated.
2. Support standard single quoted strings with doubled quotes (standard_conforming_strings=on),
   double quoted identifiers with doubled quotes, `E'...'` and `e'...'` strings with
   backslash escapes and doubled quotes, untagged `$$...$$`, and ASCII tagged dollar
   quotes (`[A-Za-z_][A-Za-z_0-9]*`). Dollar tags are case sensitive. Dollar sequences
   embedded in an unquoted identifier are identifier text, not quote openers; `$1`
   is not a quote delimiter. An E-string prefix must start at a token boundary.
3. Support `--` comments through CR, LF or EOF and nested `/* ... */` comments.
   Quote/comment-looking text inside another region has no independent meaning.
4. Reject unterminated string, identifier, dollar quote or block comment with ValueError
   whose message starts `Unterminated SQL`. EOF in a line comment is valid. The entire
   current file must be split/validated before any statement from that file is executed.
5. Preserve migration discovery (only immediate `*.sql`, filename order, default path),
   UTF-8 reading, existing ledger schema, filename skip behavior, public signature and
   console summaries. Execute each resulting statement separately. Record the filename
   only after all its statements succeed. Retain one commit for ledger bootstrap and
   one per applied file. Empty/comment-only files are recorded once.
6. Real PostgreSQL: quoted semicolons, function/DO bodies and nested comments execute
   correctly. A failure rolls back all effects and the ledger row for that file;
   earlier successfully committed files remain committed. Reruns skip applied files.
7. Existing tests must pass unchanged and without skips. Add meaningful project tests.
   No new runtime dependency, SQL migration, schema change or unrelated ETL change.

Allowed candidate files: `src/migrations.py`, new `src/sql_statements.py`, new
`tests/test_migration_sql.py`. Preserve the `src.migrations.get_db_connection` patch seam.
SQL grammar validation, COPY FROM STDIN data, transaction-control statements, psql
meta commands, non-ASCII dollar tags, concurrent migration coordination and checksum
tracking are outside this task. Do not build a general SQL parser.

Environment: native WSL Linux Codex CLI 0.160.1, model `gpt-6.1-sol`, reasoning `medium`.
Python 3.14.4; dependencies exactly the starting commit's requirements.txt (copied alongside
this contract); disposable PostgreSQL 18 provisioned before freeze, exact version in runtime.json.
Same source, runtime, test facility and documentation for both configurations.

Development: Implementer may fix its own code within one invocation (900 seconds).
Tester gets requirements/public interfaces and unchanged fixtures/schema, no candidate,
implementation source/reasoning or other configuration. Tester limit 900 seconds;
Reviewer limit 360 seconds. Configuration A orchestrator limit 2400 seconds, exactly
three role subagents; Configuration B uses existing Controller and native role launcher.
No role retries, extra agents, requirement/model changes, coordinator candidate repairs
or hints from the competing configuration. Freeze each independent suite before exposure.
Shared external suite is frozen before either run and unavailable to candidates.

Order is predeclared A then B, chosen by alphabetical configuration label, not expected success.
Shared evaluation runs after both finish. Reviewer uses review-rubric.md. Record failures,
preserve rejected artifacts, and report unverified isolation as unverified.
