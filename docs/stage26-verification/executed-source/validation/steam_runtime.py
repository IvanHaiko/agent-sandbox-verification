"""Disposable native PostgreSQL/Python prerequisites for the Stage 25 experiment."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

from agent_system.artifacts import cleanup, owned_workspace, require, save
from validation.steam_workflow import fixed_source
from agent_system.native_codex_linux import NativeLinuxCodexRunner


def command(argv, **kwargs):
    return subprocess.run([str(a) for a in argv], check=True, text=True,
                          capture_output=True, timeout=180, **kwargs)


def provision(root, evidence):
    require(root.name in ('.stage25-runtime', '.stage26-runtime'), 'Unexpected runtime root')
    (root / 'packages').mkdir(parents=True, exist_ok=True)
    if not list((root / 'packages').glob('*.deb')):
        download = command(['apt-get', 'download', 'postgresql-18', 'postgresql-client-18',
            'libpq5', 'libicu78', 'liburing2', 'libnuma1', 'libxslt1.1'], cwd=root / 'packages')
        (evidence / 'runtime-download.txt').write_text(download.stdout + download.stderr)
    package_root = root / 'postgres'
    for package in (root / 'packages').glob('*.deb'):
        command(['dpkg-deb', '-x', package, package_root])
    library = package_root / 'usr/lib/x86_64-linux-gnu'
    env = dict(os.environ, LD_LIBRARY_PATH=str(library))
    binary = package_root / 'usr/lib/postgresql/18/bin'
    print(command(['ldd', binary / 'postgres'], env=env).stdout, flush=True)
    requirements = fixed_source(Path('/mnt/c/Users/4ivan/steam-etl'),
                                '0653617666399590c853c39f08e8cf97c9eca45c')['requirements.txt']
    (root / 'requirements.txt').write_bytes(requirements)
    if not (root / 'python').exists():
        command(['/usr/bin/python3', '-m', 'venv', '--copies', root / 'python'])
        pip = command([root / 'python/bin/python', '-m', 'pip', 'install',
                       '--ignore-installed', '--disable-pip-version-check', '-r', root / 'requirements.txt'],
                      env={k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')})
        (evidence / 'runtime-install.txt').write_text(pip.stdout)
    require(not (evidence / 'runtime.json').exists(), 'Database already provisioned')
    workspace = owned_workspace({'purpose.txt': 'Disposable Stage 25 PostgreSQL; no production data.\n'})
    config = {'root': str(root), 'python': str(root / 'python/bin/python'),
              'database_workspace': str(workspace), 'binary': str(binary),
              'library': str(library), 'socket': str(workspace / 'socket'),
              'database_version': command([binary / 'postgres', '--version'], env=env).stdout.strip()}
    save(evidence, 'runtime', config)
    try:
        (workspace / 'socket').mkdir(mode=0o700)
        command([binary / 'initdb', '-D', workspace / 'data', '-U', 'stage25',
                 '--auth=trust', '--no-locale', '-E', 'UTF8'], env=env)
        command([binary / 'pg_ctl', '-D', workspace / 'data', '-l', workspace / 'postgres.log',
                 '-o', f"-h '' -k {workspace / 'socket'} -p 55425", '-w', 'start'], env=env)
        config['postmaster_pid'] = int((workspace / 'data/postmaster.pid').read_text().splitlines()[0])
        save(evidence, 'runtime', config)
        print(json.dumps(config, indent=2), flush=True)
    except Exception:
        if (workspace / 'data/postmaster.pid').exists():
            command([binary / 'pg_ctl', '-D', workspace / 'data', '-w', 'stop'], env=env)
        cleanup(workspace)
        raise


def stop(root, evidence):
    config = json.loads((evidence / 'runtime.json').read_text())
    workspace = Path(config['database_workspace'])
    env = dict(os.environ, LD_LIBRARY_PATH=config['library'])
    if workspace.exists():
        if (workspace / 'data/postmaster.pid').exists():
            command([Path(config['binary']) / 'pg_ctl', '-D', workspace / 'data',
                     '-m', 'fast', '-w', 'stop'], env=env)
        log = workspace / 'postgres.log'
        if log.exists():
            (evidence / 'postgres.log').write_bytes(log.read_bytes())
        cleanup(workspace)
    require(root.resolve() == Path(config['root']).resolve() and root.name in ('.stage25-runtime', '.stage26-runtime'),
            'Unsafe runtime cleanup root')
    shutil.rmtree(root)
    save(evidence, 'runtime-cleanup', {'database_stopped': True,
         'database_workspace_removed': not workspace.exists(), 'runtime_removed': not root.exists()})


def probe(root, evidence):
    config = json.loads((evidence / 'runtime.json').read_text())
    workspace = owned_workspace({'TASK.json': '{}', 'role-input.md': 'Controller runtime probe',
                                 'scratch/.keep': ''})
    try:
        runner = NativeLinuxCodexRunner(read_paths=(root / 'python',))
        source = ('import psycopg, pytest; '
            f'connection = psycopg.connect(dbname="postgres", user="stage25", '
            f'host={config["socket"]!r}, port=55425); '
            'print(connection.execute("SELECT current_database(), version()").fetchone()); '
            'connection.close(); '
            'import socket, errno; probe_socket=socket.socket(); probe_socket.settimeout(1); '
            'denied=probe_socket.connect_ex(("127.0.0.1",9)); probe_socket.close(); '
            'print("unlisted_tcp_errno", denied); assert denied != 0')
        result = runner.sandbox(workspace, [config['python'], '-B', '-c', source],
            writable_directory='scratch', database_socket_directory=config['socket'])
        save(evidence, 'runtime-probe-contained', result)
        print(json.dumps(result, indent=2), flush=True)
        require(result['exit_code'] == 0 and result['owned_process_group_ended'],
                'Disposable PostgreSQL is inaccessible in the native sandbox')
    finally:
        cleanup(workspace)


def host_probe(root, evidence):
    """Infrastructure diagnosis only; never candidate acceptance or a model backend."""
    config = json.loads((evidence / 'runtime.json').read_text())
    source = ('import psycopg; '
        f'connection = psycopg.connect(dbname="postgres", user="stage25", '
        f'host={config["socket"]!r}, port=55425); '
        'print(connection.execute("SELECT current_database(), version()").fetchone()); '
        'connection.close()')
    result = command([config['python'], '-B', '-c', source])
    save(evidence, 'runtime-controller-diagnostic', {'returncode': result.returncode,
         'stdout': result.stdout, 'stderr': result.stderr,
         'purpose': 'Read-only prerequisite diagnosis; no candidate or acceptance tests executed'})
    print(result.stdout, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['provision', 'probe', 'host-probe', 'stop'])
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    {'provision': provision, 'probe': probe, 'host-probe': host_probe, 'stop': stop}[args.mode](
        args.root.resolve(), args.evidence.resolve())
