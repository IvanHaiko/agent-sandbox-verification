"""Offline native-launcher predicates; live WSL evidence is recorded separately."""
import json
import os
from pathlib import Path
import sys
import tomllib

import pytest

from agent_system.native_codex_linux import NativeLinuxCodexRunner, environment


@pytest.fixture
def runner():
    result = NativeLinuxCodexRunner.__new__(NativeLinuxCodexRunner)
    result.executable = '/native/bin/codex'
    result.runtime = Path('/native')
    result.version = 'offline fixture'
    return result


def outcome(workspace, **updates):
    result = {'exit_code': 0, 'stdout': 'private narration',
        'stderr': 'model: gpt-6.1-sol\nsession id: fresh-fixture\nprovider: openai\n',
        'timed_out': False, 'owned_process_group_ended': True}
    result.update(updates)
    return result


def setup(runner, monkeypatch, root, mutation, **updates):
    (root / 'src').mkdir()
    (root / 'src/candidate.py').write_bytes(b'stub')
    (root / 'TASK.json').write_text('{}')
    monkeypatch.setattr(runner, 'sandbox', lambda workspace, *a, **k:
        outcome(workspace, stdout=str(workspace)))
    def process(argv, workspace, *a):
        mutation(workspace)
        return outcome(workspace, **updates)
    monkeypatch.setattr(runner, '_process', process)


def execute(runner, root):
    return runner.run(trial_id='offline', role='implementer', workspace=root,
        target='src/candidate.py', prompt='bounded input', verify=lambda b: {'valid': b == b'candidate'})


def candidate(workspace):
    (workspace / 'src/candidate.py').write_bytes(b'candidate')


def test_success_requires_native_identity_and_artifacts(runner, monkeypatch, tmp_path):
    setup(runner, monkeypatch, tmp_path, candidate)
    receipt = execute(runner, tmp_path)
    assert receipt['execution_status'] == 'completed'
    assert receipt['candidate_status'] == 'unaccepted'
    assert receipt['changed_files'] == ['src/candidate.py']
    assert receipt['artifact_hashes']['src/candidate.py']
    assert receipt['diff'].startswith('--- a/src/candidate.py')
    assert 'private narration' not in json.dumps(receipt)


@pytest.mark.parametrize('updates', [
    {'exit_code': 1}, {'timed_out': True}, {'owned_process_group_ended': False},
    {'stderr': 'model: another-model\nsession id: fresh-fixture'},
    {'stderr': 'model: gpt-6.1-sol'},
])
def test_native_failure_cannot_be_replaced_by_valid_candidate(runner, monkeypatch, tmp_path, updates):
    setup(runner, monkeypatch, tmp_path, candidate, **updates)
    assert execute(runner, tmp_path)['execution_status'] == 'unrecoverable'


@pytest.mark.parametrize('path', ['TASK.json', 'src/unapproved.py', '.git/config'])
def test_every_workspace_mutation_is_compared(runner, monkeypatch, tmp_path, path):
    def mutation(workspace):
        candidate(workspace)
        other = workspace / path
        other.parent.mkdir(exist_ok=True)
        other.write_text('unauthorized change')
    setup(runner, monkeypatch, tmp_path, mutation)
    receipt = execute(runner, tmp_path)
    assert receipt['execution_status'] == 'unrecoverable'
    assert not receipt['mutation_scope_valid']


def test_failed_preflight_does_not_execute_role(runner, monkeypatch, tmp_path):
    setup(runner, monkeypatch, tmp_path, lambda _: pytest.fail('Role started after failed preflight'))
    monkeypatch.setattr(runner, 'sandbox', lambda *a, **k: outcome(tmp_path, exit_code=1))
    receipt = execute(runner, tmp_path)
    assert receipt['failure_category'] == 'native_sandbox_preflight'


@pytest.mark.parametrize('target', ['../escape', '/outside/artifact', 'root-file'])
def test_target_must_be_a_bounded_subtree(runner, tmp_path, target):
    if target.startswith('/'):
        target = str(tmp_path / 'outside' / 'artifact')
    with pytest.raises(RuntimeError, match='bounded workspace subtree'):
        runner.run(trial_id='offline', role='implementer', workspace=tmp_path,
            target=target, prompt='', verify=lambda _: {'valid': True})


def test_read_only_output_uses_same_native_route_and_rejects_mutation(runner, monkeypatch, tmp_path):
    workspace = tmp_path / 'role'
    workspace.mkdir()
    (workspace / 'TASK.json').write_text('{}')
    (workspace / 'schema.json').write_text('{}')
    output = tmp_path / 'result.json'
    monkeypatch.setattr(runner, 'sandbox', lambda w, *a, **k: outcome(w, stdout=str(w)))
    def process(argv, w, *a):
        assert '--output-schema' in argv and '--output-last-message' in argv
        assert '--ephemeral' in argv and argv[argv.index('--model') + 1] == 'gpt-6.1-sol'
        output.write_text('{}')
        (w / 'TASK.json').write_text('mutated')
        return outcome(w)
    monkeypatch.setattr(runner, '_process', process)
    receipt = runner.run_read_only(trial_id='offline', role='reviewer', workspace=workspace,
        output=output, prompt='', verify=lambda _: {'valid': True})
    assert receipt['execution_status'] == 'unrecoverable'
    assert receipt['changed_files'] == ['TASK.json']


def test_schema_output_must_be_a_fresh_external_controller_file(runner, tmp_path):
    with pytest.raises(RuntimeError, match='fresh Controller artifact'):
        runner.run_read_only(trial_id='offline', role='reviewer', workspace=tmp_path,
            output=tmp_path / 'output.json', prompt='', verify=lambda _: {'valid': True})


def test_profile_keeps_isolation_and_native_settings(runner, tmp_path):
    argv = runner.command(tmp_path, 'gpt-6.1-sol', 'medium', 'src')
    settings = {}
    for i, arg in enumerate(argv):
        if arg == '-c':
            settings.update(tomllib.loads(argv[i + 1]))
    profile = settings['permissions']['role_workspace']
    assert profile['filesystem'][':workspace_roots'] == {'.': 'read', 'src': 'write'}
    assert profile['filesystem'][':tmpdir'] == profile['filesystem'][':slash_tmp'] == 'deny'
    assert ':root' not in profile['filesystem']
    assert profile['network'] == {'enabled': False}
    assert settings['model_reasoning_effort'] == 'medium'
    assert settings['features']['multi_agent'] is False
    assert '--no-daemon' in argv and '--ignore-user-config' in argv and '--ephemeral' in argv
    assert 'resume' not in argv and 'fork' not in argv


def test_environment_drops_inherited_chat_and_api_credentials(monkeypatch):
    for key in ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_ACCESS_TOKEN', 'CODEX_THREAD_ID',
                'CODEX_SESSION_ID', 'CODEX_APP_TOOLS_PIPE_PATH', 'CODEX_PERMISSION_PROFILE']:
        monkeypatch.setenv(key, 'fixture')
    monkeypatch.setenv('CODEX_HOME', 'native-owned-login')
    clean = environment()
    assert all(key not in clean for key in ['OPENAI_API_KEY', 'OPENAI_BASE_URL', 'CODEX_ACCESS_TOKEN',
        'CODEX_THREAD_ID', 'CODEX_SESSION_ID', 'CODEX_APP_TOOLS_PIPE_PATH', 'CODEX_PERMISSION_PROFILE'])
    assert clean['CODEX_HOME'] == 'native-owned-login'


@pytest.mark.skipif(os.name == 'nt', reason='Linux process-group lifecycle; verified inside WSL')
def test_owned_process_group_timeout(runner, tmp_path):
    receipt = runner._process([sys.executable, '-c', 'import time; time.sleep(30)'], tmp_path, '', .1)
    assert receipt['timed_out'] and receipt['exit_code'] != 0
    assert receipt['owned_process_group_ended']
