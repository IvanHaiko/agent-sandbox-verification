"""Controller artifact integrity and owned-workspace lifecycle."""
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

def snapshot(root):
    result = {}
    for path in Path(root).rglob('*'):
        if path.is_symlink():
            raise RuntimeError('Linked workspace entry')
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise RuntimeError('Hard-linked workspace file')
            result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(directory, name, value):
    path = directory / (name + '.json')
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding='utf-8')
    return path


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def owned_workspace(files):
    path = Path(tempfile.mkdtemp(prefix='codex-role-', dir=Path.home())).resolve()
    for name, data in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    for args in (['init', '--initial-branch=main'], ['add', '.'],
            ['-c', 'user.name=Codex Controller', '-c', 'user.email=controller@example.invalid',
             'commit', '-m', 'Freeze isolated role input']):
        subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=15, check=True)
    return path


def cleanup(path):
    require(path.parent == Path.home().resolve() and path.name.startswith('codex-role-')
            and not path.is_symlink(), 'Unsafe role cleanup root')
    snapshot(path)
    shutil.rmtree(path)
    require(not path.exists(), 'Role cleanup failed')


def archive(directory, name, data):
    path = directory / name
    path.write_bytes(data)
    require(path.read_bytes() == data, 'Archive bytes mismatch')
    return path


def freeze_design(directory, design_bytes, contract):
    contract.validate_design(design_bytes)
    design = contract.strict_json(design_bytes.decode())
    harness = contract.acceptance_source(design).encode('utf-8')
    ast.parse(harness.decode())
    archive(directory, 'frozen-test-design.json', design_bytes)
    archive(directory, 'frozen-acceptance.py', harness)
    receipt = {'design_sha256': digest(design_bytes), 'harness_sha256': digest(harness),
        'task_sha256': digest((directory / 'frozen-task.json').read_bytes()),
        'frozen_at': time.time(), 'sequence': 1, 'candidate_visible_during_design': False,
        'tester_execution_ended': True, 'tester_sessions': 1,
        'test_context_keys': ['task', 'public_interface', 'acceptance_criteria', 'constraints', 'schema']}
    save(directory, 'test-freeze', receipt)
    return receipt, harness, design


def require_frozen(directory, freeze):
    require(digest((directory / 'frozen-test-design.json').read_bytes()) == freeze['design_sha256'],
            'Frozen test design changed')
    require(digest((directory / 'frozen-acceptance.py').read_bytes()) == freeze['harness_sha256'],
            'Frozen acceptance harness changed')
    require(digest((directory / 'frozen-task.json').read_bytes()) == freeze['task_sha256'],
            'Frozen task changed')



def changed_files(before, after):
    return sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))

def artifact_diff(before, after, target):
    return ''.join(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
        fromfile='a/' + target, tofile='b/' + target))
