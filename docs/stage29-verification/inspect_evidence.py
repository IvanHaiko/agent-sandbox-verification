"""Read-only source/archive inventory; no model calls, imports or extraction."""
import ast
import hashlib
import json
import os
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(name, value):
    (E / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')

def snapshot():
    result = {}
    for directory, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [d for d in dirs if d != 'stage29-verification']
        for name in sorted(dirs + files):
            p = Path(directory) / name
            if name in ('STAGE29_ARCHITECTURE_DECISION.md', 'STAGE29_SIMPLIFICATION_PLAN.md', 'stage29-delivery.zip'):
                continue
            key = p.relative_to(ROOT).as_posix()
            try:
                if p.is_symlink():
                    result[key] = 'LINK:' + os.readlink(p)
                elif p.is_file():
                    result[key] = sha(p.read_bytes())
            except OSError as error:
                result[key] = 'UNREADABLE:' + str(error.winerror if hasattr(error, 'winerror') else error.errno)
    return result

if sys.argv[1] == 'before':
    write('workspace-before.json', snapshot())
    inventory = []
    for directory in ('agent_system', 'validation', 'tests'):
        for p in sorted((ROOT / directory).glob('*.py')):
            s = p.read_text(encoding='utf-8-sig')
            tree = ast.parse(s)
            imports = sorted(set(n.module or '' for n in ast.walk(tree) if isinstance(n, ast.ImportFrom))
                             | set(a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names))
            inventory.append(dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size,
                physical_lines=len(s.splitlines()), nonblank_noncomment_lines=sum(bool(l.strip()) and not l.lstrip().startswith('#') for l in s.splitlines()),
                sha256=sha(p.read_bytes()), imports=imports,
                definitions=[dict(name=n.name, line=n.lineno, kind=type(n).__name__) for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef))]))
    write('source-inventory.json', inventory)
    archives = []
    for stage in (27, 28):
        p = ROOT / f'docs/stage{stage}-verification/stage{stage}-delivery.zip'
        with zipfile.ZipFile(p) as z:
            bad = z.testzip()
            names = z.namelist()
            selected = [n for n in names if n.endswith(('controller-decision.json', 'quality-analysis.json', 'evaluation-summary.json', 'final-integrity.json', 'reviewer-result.json', 'permission-probe.json'))]
            members = {n: dict(sha256=sha(z.read(n)), bytes=len(z.read(n))) for n in selected}
            # Read archived evidence itself, retaining compact JSON outcomes rather than duplicate logs.
            contents = {}
            for n in selected:
                try:
                    contents[n] = json.loads(z.read(n))
                except (ValueError, UnicodeError):
                    pass
            write(f'stage{stage}-selected-evidence.json', contents)
            receipt = json.loads((p.parent / 'delivery-receipt.json').read_text())
            archives.append(dict(stage=stage, sha256=sha(p.read_bytes()), recorded_sha256=receipt['sha256'],
                digest_matches=sha(p.read_bytes()) == receipt['sha256'], crc_error=bad, member_count=len(names), selected_members=members))
    write('previous-archives-audit.json', archives)
else:
    before = json.loads((E / 'workspace-before.json').read_text())
    after = snapshot()
    write('workspace-after.json', after)
    write('workspace-integrity.json', dict(unchanged=before == after,
        added=sorted(after.keys()-before.keys()), removed=sorted(before.keys()-after.keys()),
        changed=sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
        scope='Every pre-existing workspace file, including historical evidence and caches; Stage 29 outputs excluded'))
print(sys.argv[1], 'complete')
