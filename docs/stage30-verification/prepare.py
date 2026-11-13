"""One-time Stage 30 rollback and read-only integrity inventory."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent
os.environ['GIT_OPTIONAL_LOCKS'] = '0'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def historical():
    paths = [p for n in range(25, 30) for p in (ROOT / 'docs' / f'stage{n}-verification').rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
    paths += list(ROOT.glob('STAGE2[5-9]*.md')) + list(ROOT.glob('stage2[5-9]*.zip'))
    return {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in sorted(paths)}


def original():
    repo = Path('/mnt/c/Users/4ivan/steam-etl')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repo), *args])
    names = set(git('ls-files', '-z', '--cached', '--others', '--exclude-standard').decode().split('\0')) - {''}
    files = {n: sha((repo / n).read_bytes()) if (repo / n).is_file() else None for n in sorted(names)}
    index = Path(git('rev-parse', '--git-path', 'index').decode().strip())
    if not index.is_absolute():
        index = repo / index
    registry = repo / '.git/worktrees'
    return {'head': git('rev-parse', 'HEAD').decode().strip(),
            'branch': git('symbolic-ref', '--short', 'HEAD').decode().strip(),
            'status': git('status', '--porcelain=v1', '-uall').decode(),
            'index': sha(index.read_bytes()), 'staged': sha(git('diff', '--cached', '--binary')),
            'working': sha(git('diff', '--binary')), 'files': files,
            'worktree_registry': {p.relative_to(registry).as_posix(): sha(p.read_bytes())
                                 for p in registry.rglob('*') if p.is_file()}}


if __name__ == '__main__':
    import sys
    mode = sys.argv[1]
    if mode == 'rollback':
        paths = [p for folder in ('agent_system', 'validation', 'tests')
                 for p in (ROOT / folder).glob('*.py')]
        paths += [ROOT / n for n in ('README.md', 'pyproject.toml', '.gitignore')]
        data = {p.relative_to(ROOT).as_posix(): p.read_bytes() for p in paths}
        target = E / 'source-rollback.zip'
        assert not target.exists()
        with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED) as archive:
            for name, value in data.items():
                archive.writestr(name, value)
        with zipfile.ZipFile(target) as archive:
            assert archive.testzip() is None
            assert all(archive.read(n) == b for n, b in data.items())
        result = {'archive_sha256': sha(target.read_bytes()), 'files': {n: sha(b) for n, b in data.items()},
                  'active_source_files': len([n for n in data if n.endswith('.py') and not n.startswith('tests/')]),
                  'active_physical_lines': sum(len(b.splitlines()) for n, b in data.items()
                                               if n.endswith('.py') and not n.startswith('tests/')),
                  'entry_points': ['validation.native_workflow', 'validation.steam_workflow',
                                   'validation.steam_refactoring', 'validation.steam_runtime',
                                   'validation.steam_negative_control', 'validation.steam_resume_acceptance',
                                   'validation.steam_sandbox_probe']}
        (E / 'rollback.json').write_text(json.dumps(result, indent=2))
        (E / 'historical-before.json').write_text(json.dumps(historical(), indent=2))
    elif mode.startswith('original-'):
        result = original()
        (E / (mode + '.json')).write_text(json.dumps(result, indent=2))
        if mode == 'original-after':
            assert result == json.loads((E / 'original-before.json').read_text())
    elif mode == 'historical-after':
        result = historical()
        assert result == json.loads((E / 'historical-before.json').read_text())
        (E / 'historical-integrity.json').write_text(json.dumps({'unchanged': True, 'files': len(result)}, indent=2))
    print(mode + ': verified')
