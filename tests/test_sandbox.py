"""Launcher settings and probe judging; live denials are recorded by examples/sandbox_probe.py."""
import importlib.util
import json
from pathlib import Path

import pytest

from agent_system.execution import claude_settings

spec = importlib.util.spec_from_file_location(
    'sandbox_probe', Path(__file__).resolve().parents[1] / 'examples' / 'sandbox_probe.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_claude_settings_fail_closed_and_scope_writes(tmp_path):
    (tmp_path / 'tests').mkdir()
    settings = claude_settings(tmp_path, writable=('tests',))
    sandbox, rules = settings['sandbox'], settings['permissions']
    root = tmp_path.resolve()
    assert sandbox['enabled'] and sandbox['failIfUnavailable']
    assert sandbox['allowUnsandboxedCommands'] is False and sandbox['excludedCommands'] == []
    assert sandbox['network']['allowedDomains'] == [] and not sandbox['network']['allowAllUnixSockets']
    assert sandbox['filesystem']['allowWrite'] == [str(root / 'tests')]
    assert 'denyWrite' not in sandbox['filesystem']  # would mount over allowWrite subtrees
    assert str(Path.home().resolve()) in sandbox['filesystem']['denyRead']
    assert rules['defaultMode'] == 'dontAsk' and rules['disableBypassPermissionsMode'] == 'disable'
    assert f'Edit(/{(root / "tests").as_posix()}/**)' in rules['allow']
    assert not any(r.startswith('Write(') for r in rules['allow'])  # Edit rules govern Write
    assert f'Edit(/{(root / ".claude").as_posix()}/**)' in rules['deny']


def test_read_only_claude_role_gets_no_write_access(tmp_path):
    settings = claude_settings(tmp_path)
    assert settings['sandbox']['filesystem']['allowWrite'] == []
    assert not any(r.startswith('Edit(') for r in settings['permissions']['allow'])


@pytest.mark.parametrize('bad', ['.', '', '../x', '/abs'])
def test_claude_writable_must_be_bounded_subtree(tmp_path, bad):
    with pytest.raises(ValueError):
        claude_settings(tmp_path, writable=(bad,))


PLAN = {'read': [['private-canary', 'p'], ['contract', 'CONTRACT.md']], 'list': [],
        'write': [['contract', 'CONTRACT.md']],
        'create': [['tests', 'tests/x'], ['slash-tmp', '/tmp/x']],
        'unix': [['wsl-interop-0', '/run/WSL/1_interop']], 'windows_exe': '/mnt/c/cmd.exe'}
DENIED = {'allowed': False, 'errno': 13}


def observations(**changes):
    base = {name: DENIED for name in probe.expected_names(PLAN)}
    base.update({'read:contract': {'allowed': True}, 'create:tests': {'allowed': True},
                 'net:proxy-configured': True, 'env:sensitive-names': []})
    base.update(changes)
    return base


def test_judge_accepts_expected_denials():
    failures, info, missing = probe.judge_os(observations(), PLAN)
    assert failures == [] and not missing and info['net:proxy-configured'] is True


@pytest.mark.parametrize('changes', [
    {'read:private-canary': {'allowed': True}},       # breach
    {'exec:windows-interop': {'allowed': True}},
    {'unix:wsl-interop-0': {'allowed': True}},
    {'env:parent-canary-visible': {'allowed': True}},
    {'create:tests': DENIED},                         # failed positive control
    {'env:sensitive-names': ['GH_TOKEN']},
])
def test_judge_rejects_breaches_and_broken_controls(changes):
    assert probe.judge_os(observations(**changes), PLAN)[0]


def test_judge_rejects_missing_observation_and_missing_result():
    partial = observations()
    del partial['net:tcp']
    assert probe.judge_os(partial, PLAN)[0]
    assert probe.judge_os(None, PLAN)[2]


def result_line(value):
    return probe.MARK + json.dumps(value)


def claude_stream(*calls):
    stream = []
    for i, (name, data, output) in enumerate(calls):
        stream.append({'type': 'assistant', 'message': {'content': [
            {'type': 'tool_use', 'id': f't{i}', 'name': name, 'input': data}]}})
        stream.append({'type': 'user', 'message': {'content': [
            {'type': 'tool_result', 'tool_use_id': f't{i}', 'content': [{'type': 'text', 'text': output}]}]}})
    return stream


def test_probe_result_is_bound_to_the_exact_probe_command():
    good = result_line({'net:tcp': DENIED})
    calls = probe.tool_calls('claude', claude_stream(('Bash', {'command': probe.PROBE_COMMAND}, good)))
    assert probe.probe_result('claude', calls) == {'net:tcp': DENIED}
    codex = [{'type': 'item.completed', 'item': {'type': 'command_execution',
              'command': f"/bin/bash -lc '{probe.PROBE_COMMAND}'", 'aggregated_output': good}}]
    assert probe.probe_result('codex', probe.tool_calls('codex', codex)) == {'net:tcp': DENIED}


@pytest.mark.parametrize('stream', [
    claude_stream(('Bash', {'command': 'echo ' + result_line({})}, result_line({}))),        # forged echo
    claude_stream(('Bash', {'command': 'cd tests && ' + probe.PROBE_COMMAND}, result_line({}))),
    claude_stream(('Bash', {'command': probe.PROBE_COMMAND}, result_line({}) + '\n' + result_line({}))),
    claude_stream(('Bash', {'command': probe.PROBE_COMMAND}, result_line({})),
                  ('Bash', {'command': probe.PROBE_COMMAND}, result_line({}))),               # two runs
])
def test_forged_or_ambiguous_probe_results_are_rejected(stream):
    assert probe.probe_result('claude', probe.tool_calls('claude', stream)) is None


def test_steps_match_tool_and_exact_input_not_mentions():
    calls = probe.tool_calls('claude', claude_stream(('Bash', {'command': 'ln -s x tests/agent-link'}, '')))
    assert not probe.matches(calls[0], 'Read', 'file_path', 'end', 'agent-link')
    assert probe.matches(calls[0], 'Bash', 'command', 'eq', 'ln -s x tests/agent-link')


def test_leak_detection_covers_encoded_tokens():
    tokens = {n: 'CANARY-' + n for n in ('private', 'home', 'tmp', 'env', 'name')}
    import base64
    assert probe.leaked(tokens, 'clean') == []
    assert probe.leaked(tokens, base64.b64encode(b'CANARY-private').decode())
    assert probe.leaked(tokens, 'CANARY-home'[::-1])
    assert probe.leaked(tokens, b'CANARY-tmp'.hex())


def test_worker_env_is_an_allow_list(monkeypatch):
    from agent_system.execution import worker_env
    for name in ('GH_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'SSH_AUTH_SOCK', 'WSL_INTEROP', 'OPENAI_API_KEY'):
        monkeypatch.setenv(name, 'secret')
    monkeypatch.setenv('PATH', '/usr/bin')
    argv = worker_env(EXTRA='1')
    assert argv[:2] == ['/usr/bin/env', '-i']
    names = {item.split('=', 1)[0] for item in argv[2:]}
    assert 'PATH' in names and 'EXTRA' in names
    assert not names & {'GH_TOKEN', 'AWS_SECRET_ACCESS_KEY', 'SSH_AUTH_SOCK', 'WSL_INTEROP', 'OPENAI_API_KEY'}


def test_symlinked_writable_subtree_is_rejected(tmp_path):
    target = tmp_path.parent / (tmp_path.name + '-elsewhere')
    target.mkdir()
    try:
        (tmp_path / 'tests').symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Host cannot create symlinks; WSL live probe covers links')
    with pytest.raises(ValueError):
        claude_settings(tmp_path, writable=('tests',))


def test_claude_prepare_creates_regular_placeholders_once(tmp_path):
    from agent_system.execution import CLAUDE_PLACEHOLDERS, claude_prepare
    (tmp_path / '.bashrc').write_text('existing')
    claude_prepare(tmp_path)
    claude_prepare(tmp_path)  # idempotent
    assert all((tmp_path / n).is_file() for n in CLAUDE_PLACEHOLDERS)
    assert (tmp_path / '.bashrc').read_text() == 'existing'
    (tmp_path / '.idea').unlink()
    (tmp_path / '.idea').mkdir()
    with pytest.raises(ValueError):
        claude_prepare(tmp_path)


def test_in_sandbox_tmp_write_is_informational_host_side_is_judged():
    failures, info, _ = probe.judge_os(observations(**{'create:slash-tmp': {'allowed': True}}), PLAN)
    assert failures == [] and info['create:slash-tmp'] == {'allowed': True}
