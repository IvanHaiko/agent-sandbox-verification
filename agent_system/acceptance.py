"""Source-only workspaces, immutable test versions and one deterministic final gate."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    if not isinstance(name, str):
        raise ValueError('Expected an exact relative POSIX file path')
    p = PurePosixPath(name)
    if ('\\' in name or ':' in name or p.is_absolute()
            or '..' in p.parts or not p.parts or p.as_posix() != name):
        raise ValueError('Expected an exact relative POSIX file path')
    return p


def snapshot(root):
    """All regular files, including hidden/untracked files. Reject links, never follow them.

    Strict roles use source-only exports, so no .git object database is hashed.
    """
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('Workspace must be a real directory')
    result = {}
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in [*dirs, *files]:
            path = Path(directory) / name
            mode = path.lstat()
            if stat.S_ISLNK(mode.st_mode) or getattr(path, 'is_junction', lambda: False)():
                raise ValueError('Linked workspace entry: ' + str(path))
            if name in files:
                if not stat.S_ISREG(mode.st_mode) or mode.st_nlink != 1:
                    raise ValueError('Nonregular or hard-linked workspace entry: ' + str(path))
                result[path.relative_to(root).as_posix()] = path.read_bytes()
    return result


def workspace(files):
    """Public inputs are selected explicitly by the parent, never recursively copied."""
    for name, value in files.items():
        relative(name)
        if name == '.codex-owned' or not isinstance(value, (str, bytes)):
            raise ValueError('Invalid public input')
    root = Path(tempfile.mkdtemp(prefix='codex-role-', dir=Path.home())).resolve()
    (root / '.codex-owned').write_text('Native Codex disposable source workspace\n')
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value.encode() if isinstance(value, str) else value)
    return root


def preserve(root, destination, outcome):
    """Copy exact regular bytes before cleanup, including rejected/unapproved files.

    Linked entries are recorded as diagnostics without dereferencing outside inputs.
    An exclusive archive prevents an earlier failed result being overwritten.
    """
    root, destination = Path(root), Path(destination)
    if root.is_symlink() or destination.is_relative_to(root.absolute()):
        raise ValueError('Evidence must be outside the owned workspace')
    links = {}
    with zipfile.ZipFile(destination, 'x', zipfile.ZIP_DEFLATED) as archive:
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in [*dirs, *files]:
                path = Path(directory) / name
                key = path.relative_to(root).as_posix()
                mode = path.lstat()
                if stat.S_ISLNK(mode.st_mode):
                    links[key] = os.readlink(path)
                elif getattr(path, 'is_junction', lambda: False)():
                    links[key] = '<junction>'
                    if name in dirs:
                        dirs.remove(name)
                elif stat.S_ISREG(mode.st_mode):
                    if mode.st_nlink != 1:
                        links[key] = '<hardlink; contents not read>'
                    else:
                        archive.writestr('files/' + key, path.read_bytes())
                elif not stat.S_ISDIR(mode.st_mode):
                    links[key] = '<nonregular>'
        archive.writestr('outcome.json', json.dumps(outcome, indent=2))
        archive.writestr('links.json', json.dumps(links, indent=2))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('Evidence archive verification failed')
    return digest(destination.read_bytes())


def cleanup(root, *, preserved):
    root = Path(root).absolute()
    receipt = Path(preserved)
    marker = root / '.codex-owned'
    if (root.parent != Path.home().resolve() or not root.name.startswith('codex-role-')
            or root.is_symlink() or getattr(root, 'is_junction', lambda: False)()
            or not marker.is_file() or marker.is_symlink()
            or marker.read_text() != 'Native Codex disposable source workspace\n'
            or not receipt.is_file() or receipt.is_symlink() or receipt.is_relative_to(root)):
        raise ValueError('Unsafe cleanup or missing preserved evidence')
    with zipfile.ZipFile(receipt) as archive:
        if archive.testzip() is not None or 'outcome.json' not in archive.namelist():
            raise ValueError('Invalid preservation archive')
        recorded = json.loads(archive.read('outcome.json'))
        if recorded.get('workspace') != str(root):
            raise ValueError('Preservation archive belongs to another workspace')
        # Refuse to delete bytes produced since preservation. Links are never followed.
        for directory, _, files in os.walk(root, followlinks=False):
            for name in files:
                path = Path(directory) / name
                if (not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
                        and path.lstat().st_nlink == 1):
                    if archive.read('files/' + path.relative_to(root).as_posix()) != path.read_bytes():
                        raise ValueError('Workspace changed after preservation')
    shutil.rmtree(root)


def freeze(files, destination):
    """A fresh version of executable tests/contract; caller keeps hashes out of worker reach."""
    for name in files:
        relative(name)
    destination = Path(destination)
    destination.mkdir(exist_ok=False)
    for name, value in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return {name: digest(value) for name, value in snapshot(destination).items()}


def accept(root, baseline, *, allowed, required, processes, checks,
           frozen_root=None, frozen_hashes=None, review=None, environment_errors=()):
    """No execution, scheduling or retries: evaluate observed facts, fail closed."""
    failures = []
    def fail(group, detail):
        failures.append({'group': group, 'detail': detail})
    for name in [*allowed, *required]:
        relative(name)
    changed = []
    try:
        final = snapshot(root)
        changed = sorted(n for n in baseline.keys() | final.keys() if baseline.get(n) != final.get(n))
        if set(changed) - set(allowed):
            fail('artifact/scope', 'Unauthorized changes: ' + repr(sorted(set(changed) - set(allowed))))
        missing = set(required) - final.keys()
        if missing:
            fail('artifact/scope', 'Missing required final files: ' + repr(sorted(missing)))
        if frozen_root is not None:
            actual = {n: digest(b) for n, b in snapshot(frozen_root).items()}
            if not frozen_hashes or actual != frozen_hashes:
                fail('artifact/scope', 'Frozen acceptance version changed')
        elif frozen_hashes is not None:
            fail('artifact/scope', 'Frozen acceptance directory missing')
    except (ValueError, OSError) as error:
        final = {}
        fail('artifact/scope', str(error))
    if not processes:
        fail('process/environment', 'No observed execution result')
    for name, result in processes.items():
        if (type(result.get('exit_code')) is not int or result['exit_code'] != 0
                or result.get('timed_out') is not False
                or result.get('owned_process_group_ended') is not True):
            fail('process/environment', 'Unsuccessful execution/shutdown: ' + name)
    if not checks:
        fail('behavior/review', 'No required project check result')
    for name, result in checks.items():
        if (type(result.get('exit_code')) is not int or result['exit_code'] != 0
                or result.get('timed_out') is not False
                or result.get('owned_process_group_ended') is not True):
            fail('behavior/review', 'Required check failed or incomplete: ' + name)
    if review is not None and (review.get('accepted') is not True or review.get('blockers') != []):
        fail('behavior/review', 'Review missing acceptance or has blockers')
    for error in environment_errors:
        fail('process/environment', str(error))
    return {'accepted': not failures, 'failures': failures, 'changed_files': changed,
            'final_hashes': {n: digest(b) for n, b in final.items()},
            'processes': processes, 'checks': checks, 'review': review}
