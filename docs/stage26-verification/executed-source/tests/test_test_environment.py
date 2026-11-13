"""Check service boundaries and failure propagation, without native model calls."""
import json
import time

import pytest

from agent_system.test_environment import CLIENT, RoleTestEnvironment


def test_service_rejects_commands_and_cleans_exchange(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    for name, data in RoleTestEnvironment.inputs().items():
        path = workspace / name
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(data)
    service = RoleTestEnvironment(None, {}, tmp_path, {'unit': ['pytest', 'tests']})
    service.start(workspace)
    (workspace / 'checks/request.json').write_text(json.dumps({'check': 'arbitrary shell'}))
    deadline = time.monotonic() + 3
    response = workspace / 'checks/response.json'
    while not response.exists() and time.monotonic() < deadline:
        time.sleep(.05)
    assert json.loads(response.read_text())['exit_code'] == 2
    service.finish()
    assert list((workspace / 'checks').iterdir()) == [workspace / 'checks/.keep']
    assert not service.thread.is_alive()
    assert (workspace / 'controller-check.py').read_bytes() == CLIENT.encode()


def test_checks_are_read_only_and_record_exact_source_and_failure(tmp_path):
    workspace = tmp_path / 'workspace'
    (workspace / 'checks').mkdir(parents=True)
    (workspace / 'source.py').write_text('candidate')
    class Runner:
        def sandbox(self, root, argv, **kwargs):
            assert kwargs['writable_directory'] == 'checks/scratch'
            assert kwargs['database_socket_directory'] == '/owned/socket'
            assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1' in argv
            (root / 'checks/scratch/results.xml').write_text('<testsuites/>')
            return {'exit_code': 1, 'stdout': 'one failing test', 'stderr': '',
                    'owned_process_group_ended': True, 'timed_out': False}
    service = RoleTestEnvironment(Runner(), {'socket': '/owned/socket', 'python': '/runtime/python'},
                                  tmp_path, {'unit': ['pytest', 'tests']})
    service.workspace = workspace
    result = service.execute('unit')
    assert result['exit_code'] == 1
    assert service.results[0]['source_hashes']['source.py']
    assert (tmp_path / 'implementer-check-1.xml').exists()
    assert not (workspace / 'checks/scratch').exists()


def test_check_cannot_mutate_source(tmp_path):
    (tmp_path / 'checks').mkdir()
    (tmp_path / 'source.py').write_text('candidate')
    class Runner:
        def sandbox(self, root, *args, **kwargs):
            (root / 'source.py').write_text('corrupted')
            return {'exit_code': 0, 'stdout': '', 'stderr': '',
                    'owned_process_group_ended': True, 'timed_out': False}
    service = RoleTestEnvironment(Runner(), {'socket': '/owned/socket', 'python': '/runtime/python'},
                                  tmp_path, {'unit': ['pytest', 'tests']})
    service.workspace = tmp_path
    with pytest.raises(RuntimeError, match='read-only source'):
        service.execute('unit')
