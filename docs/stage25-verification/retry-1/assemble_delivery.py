"""Controller packaging of completed evidence; no model or target modification."""
import hashlib
import json
from pathlib import Path
import zipfile

evidence = Path(__file__).resolve().parent
root = evidence.parents[2]
readme = """Stage 25 Steam ETL delivery — PASS

Source commit: 0653617666399590c853c39f08e8cf97c9eca45c
Use a separate checkout of this commit, preserving your working branch and dirty files.
Apply from its repository root:

    git apply --check /path/to/steam-etl-implementation.patch
    git apply /path/to/steam-etl-implementation.patch

The patch contains implementation documentation and 37 new test cases.
For the additional independent tests, copy the included
tests/test_stage25_acceptance.py into that checkout's tests directory.
Install its pinned requirements in an isolated Python environment and provide a
DISPOSABLE PostgreSQL server. Read the existing tests/conftest.py for its exact
database environment variables and create/drop-database privileges. Tests create,
migrate and clean test databases; never point them at a production database.
Require actual database execution rather than fixture skips:

    REQUIRE_DB_TESTS=1 python -m pytest -q -p no:cacheprovider --junitxml=acceptance.xml

Recorded results: 234 passed, zero failures/errors/skips, including 29 independent
cases. The same independent suite on the unchanged commit produced 22 failures
and 7 passes. Reviewer accepted with no blockers or findings. Framework regression:
40 passed. The full assessment explains environment interventions, test scope,
ordering policies, rejection of empty observations and table-lock throughput limits.
Runtime socket paths in historical receipts no longer exist: cleanup completed.
This archive does not modify or deploy the original repository.
"""

entries = {
    'README.txt': readme.encode(),
    'STAGE25_REAL_WORLD_CODING_ASSESSMENT.md': (root / 'STAGE25_REAL_WORLD_CODING_ASSESSMENT.md').read_bytes(),
    'steam-etl-implementation.patch': (evidence / 'steam-etl-implementation.patch').read_bytes(),
    'tests/test_stage25_acceptance.py': (evidence / 'frozen-acceptance.py').read_bytes(),
}
for name in ('frozen-test-design.json', 'test-freeze.json', 'normalized-contract.json',
             'acceptance.xml', 'acceptance.json', 'acceptance-stdout.txt',
             'baseline-control.xml', 'baseline-control.json', 'reviewer-result.json',
             'controller-decision.json', 'final-integrity-audit.json', 'framework-final-wsl.xml'):
    entries['evidence/' + name] = (evidence / name).read_bytes()
entries['SHA256SUMS.json'] = json.dumps({name: hashlib.sha256(data).hexdigest()
    for name, data in sorted(entries.items())}, indent=2).encode() + b'\n'
archive = evidence / 'steam-etl-stage25-delivery.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as bundle:
    for name, data in sorted(entries.items()):
        info = zipfile.ZipInfo(name, date_time=(2026, 10, 8, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        bundle.writestr(info, data)
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert {name: bundle.read(name) for name in bundle.namelist()} == entries

manifest = {
    'authority': 'Controller',
    'outcome': 'PASS',
    'files': {p.relative_to(evidence).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(evidence.rglob('*'))
              if p.is_file() and p.name != 'evidence-manifest.json'},
    'external_documents': {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                           for name in ('README.md', 'STAGE25_REAL_WORLD_CODING_ASSESSMENT.md')},
    'zip_entries_verified': len(entries),
}
(evidence / 'evidence-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
for name, expected in manifest['files'].items():
    assert hashlib.sha256((evidence / name).read_bytes()).hexdigest() == expected
print(json.dumps({'evidence_files_hashed': len(manifest['files']),
                  'zip_entries_verified': len(entries),
                  'delivery_sha256': manifest['files'][archive.name]}, indent=2))
