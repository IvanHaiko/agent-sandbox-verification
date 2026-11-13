# Reproduce functional evidence

The archive contains the exact committed baseline in baseline-source.tar.gz,
each three-file candidate patch, frozen independent test files, the corrected
held-out suite, JUnit results and execution receipts. The original malformed
evaluator is retained as test_external_acceptance.original.py for diagnosis only.

In a fresh disposable directory for each configuration, extract the baseline,
initialize Git and commit the extracted files, then apply A/implementation.patch
or B/implementation.patch with git apply --check followed by git apply. Install
requirements.txt into a disposable Python environment. Use Python 3.14.4 and
PostgreSQL 18.6 for the recorded runtime match.

Point POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER and POSTGRES_PASSWORD at an owned
disposable PostgreSQL server. Set POSTGRES_DB=unused and a unique POSTGRES_TEST_DB
for the evaluation. Set REQUIRE_DB_TESTS=1 and PYTEST_DISABLE_PLUGIN_AUTOLOAD=1.
The original tests/conftest.py creates/drops that separate test database and
applies the original schema/migrations; it must not target a production database.

Copy test_external_acceptance.py into tests/test_stage28_evaluation.py. Run:

```text
python -B -m pytest -q -p no:cacheprovider tests/test_stage28_evaluation.py
python -B -m pytest -q -p no:cacheprovider tests
```

For independent tests, remove the copied external module and copy
A/frozen/test_independent.py or B/frozen-acceptance.py to
tests/test_stage28_evaluation.py, then run that file explicitly. Do not edit tests.
The three predeclared mutation suffixes are stored in freeze.json. Append the
selected suffix to its named source file only in a new disposable candidate copy,
then run either frozen suite. Restore a fresh candidate for every mutation.
Compare distinct detected defects, failures/errors/skips and preserved JUnit output.

The one-off experiment.py reuses the existing Stage 27 adapter and active framework
in the original workspace layout, with that host's WSL native Codex login. Its
provision/run commands consume model quota and are not necessary to reproduce the
archived engineering test results. It is not a portable orchestration platform.
All frozen inputs, source files and delivery members have SHA-256 manifests.
No candidate patch was applied to the original Steam ETL checkout.
