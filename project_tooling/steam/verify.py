"""Steam-owned verification recipe for a disposable source export, not agent orchestration.

Run from the framework checkout under WSL. Original repository is read only.
Exports one fixed commit and uses ordinary pytest/Ruff commands in native confinement.
No production .env/data, original index writes, worktrees, or model sessions.
"""
import io
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent_system.acceptance import cleanup, preserve, snapshot, workspace
from agent_system.execution import process, sandbox


def main(repository, commit, evidence):
    evidence.mkdir(parents=True, exist_ok=False)
    os.environ['GIT_OPTIONAL_LOCKS'] = '0'
    def git(*args):
        return subprocess.check_output(['git', '-C', str(repository), *args])
    assert git('rev-parse', commit + '^{commit}').decode().strip() == commit
    files = {}
    with tarfile.open(fileobj=io.BytesIO(git('archive', commit))) as archive:
        for entry in archive:
            p = PurePosixPath(entry.name)
            assert not p.is_absolute() and '..' not in p.parts
            assert entry.isdir() or entry.isfile()
            if entry.isfile():
                assert p.parts[0] != '.git' and p.name != '.env'
                files[p.as_posix()] = archive.extractfile(entry).read()
    # Ship the recipe alongside the exported project; never modify the original.
    files['tools/stage30_verify.py'] = Path(__file__).read_bytes()
    source = workspace(files)
    runtime = workspace({'purpose.txt': 'Disposable Steam verification runtime; no production data.\n'})
    result = {'source_commit': commit, 'source': str(source), 'runtime': str(runtime), 'checks': {}}
    (evidence / 'owned.json').write_text(json.dumps(result, indent=2))
    pg_started = False
    library = runtime / 'postgres/usr/lib/x86_64-linux-gnu'
    binary = runtime / 'postgres/usr/lib/postgresql/18/bin'
    def run(name, argv, cwd=runtime, timeout=180):
        outcome = process(argv, cwd, timeout=timeout)
        (evidence / (name + '.json')).write_text(json.dumps(outcome, indent=2))
        assert outcome['exit_code'] == 0 and not outcome['timed_out'] and outcome['owned_process_group_ended'], name
        return outcome
    try:
        (runtime / 'packages').mkdir()
        run('download', ['apt-get', 'download', 'postgresql-18', 'postgresql-client-18',
                         'libpq5', 'libicu78', 'liburing2', 'libnuma1', 'libxslt1.1'], runtime / 'packages')
        for index, package in enumerate(sorted((runtime / 'packages').glob('*.deb'))):
            run('extract-' + str(index), ['dpkg-deb', '-x', package, runtime / 'postgres'])
        run('venv', ['/usr/bin/python3', '-m', 'venv', '--copies', runtime / 'python'])
        python = runtime / 'python/bin/python'
        run('install', [python, '-m', 'pip', 'install', '--disable-pip-version-check',
                        '-r', source / 'requirements.txt'], timeout=240)
        pg = ['/usr/bin/env', 'LD_LIBRARY_PATH=' + str(library)]
        (runtime / 'socket').mkdir(mode=0o700)
        run('initdb', [*pg, binary / 'initdb', '-D', runtime / 'data', '-U', 'stage30',
                       '--auth=trust', '--no-locale', '-E', 'UTF8'])
        # pg_ctl starts an intentionally persistent owned service; it must not be
        # launched through the per-command process-group reaper.
        launch = subprocess.run([*map(str, pg), str(binary / 'pg_ctl'), '-D', str(runtime / 'data'),
                                 '-l', str(runtime / 'postgres.log'), '-o',
                                 f"-h '' -k {runtime / 'socket'} -p 55430", '-w', 'start'],
                                capture_output=True, text=True, timeout=30)
        (evidence / 'postgres-start.json').write_text(json.dumps({'exit_code': launch.returncode,
            'stdout': launch.stdout, 'stderr': launch.stderr}, indent=2))
        assert launch.returncode == 0
        pg_started = True
        result['postmaster_pid'] = int((runtime / 'data/postmaster.pid').read_text().splitlines()[0])
        before = snapshot(source)
        (source / 'scratch').mkdir()
        env = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
               'TMPDIR': str(source / 'scratch'), 'POSTGRES_HOST': str(runtime / 'socket'),
               'POSTGRES_PORT': '55430', 'POSTGRES_USER': 'stage30',
               'POSTGRES_PASSWORD': 'disposable-local-only', 'POSTGRES_DB': 'unused',
               'POSTGRES_TEST_DB': 'stage30_checks', 'REQUIRE_DB_TESTS': '1',
               'LD_LIBRARY_PATH': str(library)}
        prefix = ['/usr/bin/env', *[k + '=' + v for k, v in env.items()], str(python), '-B']
        checks = {
            'pytest': [*prefix, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
                       '--basetemp=scratch/tmp', '--junitxml=scratch/results.xml', 'tests'],
            'ruff': [*prefix, '-m', 'ruff', 'check', '--no-cache', 'src', 'tests'],
            'network-denial': [*prefix, '-c', 'import socket; s=socket.socket(); s.settimeout(1); '
                               'code=s.connect_ex(("127.0.0.1",9)); s.close(); '
                               'print("unlisted_tcp_errno", code); assert code != 0']}
        for name, argv in checks.items():
            outcome = sandbox(source, argv, writable=['scratch'],
                              read_paths=[runtime / 'python', library],
                              database_socket=runtime / 'socket', timeout=180)
            result['checks'][name] = dict(outcome, argv=argv)
            (evidence / (name + '.json')).write_text(json.dumps(result['checks'][name], indent=2))
        junit = source / 'scratch/results.xml'
        if junit.exists():
            (evidence / 'results.xml').write_bytes(junit.read_bytes())
        # pytest creates *current symlinks in its owned basetemp. Preserve them
        # without dereferencing, then remove only this explicitly writable scratch.
        # The source integrity check must still reject links anywhere else.
        preserve(source, evidence / 'source-with-scratch.zip', {'workspace': str(source), 'checks': result['checks']})
        scratch = source / 'scratch'
        assert scratch.parent == source and not scratch.is_symlink()
        shutil.rmtree(scratch)
        assert snapshot(source) == before
        result['source_unchanged'] = True
        result['passed'] = all(c['exit_code'] == 0 and not c['timed_out'] and c['owned_process_group_ended']
                               for c in result['checks'].values())
    finally:
        if pg_started or (runtime / 'data/postmaster.pid').exists():
            stop = subprocess.run(['/usr/bin/env', 'LD_LIBRARY_PATH=' + str(library), str(binary / 'pg_ctl'),
                                   '-D', str(runtime / 'data'), '-m', 'fast', '-w', 'stop'],
                                  capture_output=True, text=True, timeout=30)
            result['postgres_stopped'] = stop.returncode == 0 and not (runtime / 'data/postmaster.pid').exists()
            assert result['postgres_stopped']
            try:
                os.kill(result['postmaster_pid'], 0)
            except ProcessLookupError:
                result['postmaster_gone'] = True
            else:
                result['postmaster_gone'] = False
        (evidence / 'result.json').write_text(json.dumps(result, indent=2))
        # Keep logs/results/source before removal, not downloaded dependency bytes.
        for name, root in [('source', source), ('runtime', runtime)]:
            archive = evidence / (name + '-closeout.zip')
            preserve(root, archive, {'workspace': str(root), 'result': result})
            cleanup(root, preserved=archive)
        result['workspaces_removed'] = not source.exists() and not runtime.exists()
        (evidence / 'result.json').write_text(json.dumps(result, indent=2))
    assert result['passed'], result
    print('Direct project checks passed; owned PostgreSQL stopped and workspaces removed.', flush=True)


if __name__ == '__main__':
    main(Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]).resolve())
