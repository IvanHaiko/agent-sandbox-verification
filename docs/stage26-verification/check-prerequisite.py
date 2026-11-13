"""Exercise the role-facing client inside network=false before any coding role."""
import json
from pathlib import Path

from agent_system.artifacts import cleanup, owned_workspace, require, save, snapshot
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.test_environment import RoleTestEnvironment
from validation.steam_workflow import fixed_source

directory = Path(__file__).resolve().parent
runtime = json.loads((directory / 'runtime.json').read_text())
files = fixed_source(Path('/mnt/c/Users/4ivan/steam-etl'), '0653617666399590c853c39f08e8cf97c9eca45c')
files.update(RoleTestEnvironment.inputs())
workspace = owned_workspace(files)
runner = NativeLinuxCodexRunner(read_paths=(Path(runtime['root']) / 'python',))
service = RoleTestEnvironment(runner, runtime, directory, {'integration': ['pytest', 'tests']},
                              database='stage26_prerequisite', evidence_prefix='prerequisite-check')
try:
    before = snapshot(workspace)
    service.start(workspace)
    try:
        result = runner.sandbox(workspace, ['/usr/bin/python3', '-B', 'controller-check.py', 'integration'],
                                writable_directory='checks', timeout=240)
    finally:
        service.finish()
    save(directory, 'role-facing-test-probe', dict(result, role_network_enabled=False,
        workspace_unchanged=snapshot(workspace) == before, model_requests=0))
    require(result['exit_code'] == 0 and result['owned_process_group_ended'] and
            snapshot(workspace) == before, 'Role-facing functional checks failed')
    print(result['stdout'], flush=True)
finally:
    cleanup(workspace)
