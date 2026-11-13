"""Retrospective read-only probe of A's recorded parent permission profile."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.artifacts import save

e = Path(__file__).resolve().parent
start = json.loads((e / 'A/start.json').read_text())
argv = start['command']
root = Path(argv[argv.index('--cd') + 1])
runtime = json.loads((e / 'runtime.json').read_text())
profile = next(arg for arg in argv if arg.startswith('permissions.role_workspace='))
executable = argv[0]
probe = '''import json, os
paths = PATHS
result = {}
for path in paths:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError as exc:
        result[path] = {'readable': False, 'errno': exc.errno}
    else:
        os.close(fd)
        result[path] = {'readable': True}
print(json.dumps(result))
'''.replace('PATHS', repr([str(root/'implementer/src/migrations.py'),
    str(root/'tester/tests/test_independent.py'), str(e/'test_external_acceptance.py'),
    str(e/'B/candidate/src/migrations.py'), '/mnt/c/Users/4ivan/steam-etl/src/migrations.py']))
runner = NativeLinuxCodexRunner(read_paths=(Path(runtime['root'])/'python',))
result = runner._process([executable, '-c', 'default_permissions="role_workspace"', '-c', profile,
    'sandbox', '--permission-profile', 'role_workspace', '--cd', str(root),
    '/usr/bin/python3', '-I', '-B', '-c', probe], root, '', 30)
result['purpose'] = 'Same recorded parent native filesystem profile; retrospective read probe, not a subagent trace or reviewer write probe'
if result['exit_code'] == 0:
    result['paths'] = json.loads(result['stdout'])
save(e/'A', 'permission-probe', result)
print(json.dumps(result, indent=2))
