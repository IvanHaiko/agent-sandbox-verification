"""Controller-owned, predefined checks for a network-disabled native role.

The role submits a check name through its private workspace. The Controller
executes it with the existing native sandbox, never inside the model process.
There is no arbitrary command, environment override or unsandboxed fallback.
"""
import json
from pathlib import Path
import shutil
import threading
import time

from .artifacts import digest, require, save, snapshot


CLIENT = '''import json, pathlib, sys, time
root = pathlib.Path(__file__).resolve().parent / "checks"
request = root / "request.json"
response = root / "response.json"
response.unlink(missing_ok=True)
temporary = root / "request.tmp"
temporary.write_text(json.dumps({"check": sys.argv[1]}))
temporary.replace(request)
deadline = time.monotonic() + 240
while not response.exists():
    if time.monotonic() > deadline:
        raise SystemExit("Controller check timed out")
    time.sleep(.1)
result = json.loads(response.read_text())
print(result["stdout"])
print(result["stderr"], file=sys.stderr)
raise SystemExit(result["exit_code"])
'''


class RoleTestEnvironment:
    """Bounded check service; check commands and evidence are Controller-owned."""

    def __init__(self, runner, runtime, evidence, checks, *, database='role_checks', evidence_prefix='implementer-check'):
        self.runner, self.runtime, self.evidence = runner, runtime, Path(evidence)
        self.checks, self.database = checks, database
        self.evidence_prefix = evidence_prefix
        self.results = []
        self.stopping = threading.Event()
        self.error = None

    @staticmethod
    def inputs():
        return {'controller-check.py': CLIENT.encode(), 'checks/.keep': b''}

    def start(self, workspace):
        self.workspace = Path(workspace)
        require((self.workspace / 'controller-check.py').read_bytes() == CLIENT.encode(),
                'Test client changed')
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self):
        try:
            while not self.stopping.wait(.1):
                request = self.workspace / 'checks/request.json'
                if not request.exists():
                    continue
                require(not request.is_symlink() and request.stat().st_nlink == 1,
                        'Linked test request')
                value = json.loads(request.read_text())
                request.unlink()
                if not isinstance(value, dict) or set(value) != {'check'} or value['check'] not in self.checks:
                    result = {'exit_code': 2, 'stdout': '', 'stderr': 'Unknown predefined check'}
                else:
                    result = self.execute(value['check'])
                temporary = self.workspace / 'checks/response.tmp'
                require(not temporary.is_symlink(), 'Linked test response')
                temporary.write_text(json.dumps(result))
                temporary.replace(self.workspace / 'checks/response.json')
        except Exception as error:
            self.error = str(error)
            response = self.workspace / 'checks/response.json'
            if not response.is_symlink():
                response.write_text(json.dumps({'exit_code': 2, 'stdout': '', 'stderr': self.error}))

    def execute(self, name):
        """Run a check on the role's current bytes; persist evidence out of role reach."""
        check = self.checks[name]
        require(check[0] in ('pytest', 'ruff'), 'Only pytest and Ruff checks are supported')
        before = snapshot(self.workspace)
        scratch = self.workspace / 'checks/scratch'
        require(not scratch.exists(), 'Unexpected check scratch')
        scratch.mkdir()
        env = {'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
               'TMPDIR': str(scratch), 'POSTGRES_HOST': self.runtime['socket'],
               'POSTGRES_PORT': '55425', 'POSTGRES_USER': 'stage25',
               'POSTGRES_PASSWORD': 'disposable-local-only', 'POSTGRES_DB': 'unused',
               'POSTGRES_TEST_DB': self.database, 'REQUIRE_DB_TESTS': '1'}
        arguments = (['-q', '-p', 'no:cacheprovider', '--basetemp=checks/scratch/tmp',
                      '--junitxml=checks/scratch/results.xml'] if check[0] == 'pytest'
                     else ['check', '--no-cache'])
        argv = ['/usr/bin/env', *[k + '=' + v for k, v in env.items()],
                self.runtime['python'], '-B', '-m', check[0], *arguments, *check[1:]]
        try:
            result = self.runner.sandbox(self.workspace, argv, writable_directory='checks/scratch',
                database_socket_directory=self.runtime['socket'], timeout=180)
            number = len(self.results) + 1
            prefix = self.evidence_prefix + '-' + str(number)
            junit = scratch / 'results.xml'
            if junit.exists():
                (self.evidence / (prefix + '.xml')).write_bytes(junit.read_bytes())
            receipt = dict(result, check=name, argv=argv,
                source_hashes={p: digest(b) for p, b in before.items() if not p.startswith('checks/')},
                network='private user/network namespace; native filesystem sandbox; owned database socket')
            save(self.evidence, prefix, receipt)
            self.results.append(receipt)
            require(result['owned_process_group_ended'] and not result['timed_out'],
                    'Check timeout or unconfirmed shutdown')
        finally:
            require(scratch.resolve() == self.workspace / 'checks/scratch', 'Unsafe check cleanup')
            shutil.rmtree(scratch)
        after = snapshot(self.workspace)
        require({p: b for p, b in after.items() if not p.startswith('checks/')} ==
                {p: b for p, b in before.items() if not p.startswith('checks/')},
                'Check modified read-only source')
        return {k: result[k] for k in ('exit_code', 'stdout', 'stderr')}

    def finish(self):
        self.stopping.set()
        self.thread.join(timeout=190)
        require(not self.thread.is_alive() and self.error is None,
                'Controller test service failed: ' + str(self.error))
        checks = self.workspace / 'checks'
        require(checks.resolve() == self.workspace / 'checks', 'Unsafe check service cleanup')
        shutil.rmtree(checks)
        checks.mkdir()
        (checks / '.keep').write_bytes(b'')
