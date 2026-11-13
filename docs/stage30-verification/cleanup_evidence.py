"""Discard only newly generated dependency archives after retaining runtime diagnostics."""
import hashlib
import json
from pathlib import Path
import zipfile

E = Path(__file__).resolve().parent
results = []
for name in ('project', 'project-direct'):
    source = E / name / 'runtime-closeout.zip'
    target = E / name / 'runtime-diagnostics.zip'
    assert source.resolve().parent == E / name
    selected = ['files/.codex-owned', 'files/purpose.txt', 'files/postgres.log', 'outcome.json', 'links.json']
    with zipfile.ZipFile(source) as old:
        data = {n: old.read(n) for n in selected}
    with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as new:
        for n, b in data.items():
            new.writestr(n, b)
    with zipfile.ZipFile(target) as new:
        assert new.testzip() is None and all(new.read(n) == b for n, b in data.items())
    results.append({'path': str(source), 'discarded_bytes': source.stat().st_size,
                    'archive_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
                    'diagnostics': str(target), 'preserved_members': selected,
                    'reason': 'Downloaded dependencies and stopped empty test cluster; source and test outputs retained separately'})
    source.unlink()
(E / 'dependency-archive-cleanup.json').write_text(json.dumps(results, indent=2))
print('Runtime logs preserved; redundant downloaded-dependency archives removed.')
