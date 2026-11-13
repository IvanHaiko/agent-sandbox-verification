"""Focused safety regressions; real CLI/DB observations live in Stage 30 evidence."""
import json
import os
from pathlib import Path
import sys
import time
import zipfile

import pytest

from agent_system.acceptance import accept, cleanup, freeze, preserve, snapshot, workspace
from agent_system.execution import environment, process

OK = {'exit_code': 0, 'timed_out': False, 'owned_process_group_ended': True}


def gate(root, baseline, **kwargs):
    options = dict(allowed=['src/helper.py'], required=['src/main.py', 'src/helper.py'],
                   processes={'native': OK}, checks={'project': OK})
    options.update(kwargs)
    return accept(root, baseline, **options)


@pytest.fixture
def source(tmp_path):
    (tmp_path / 'src').mkdir()
    (tmp_path / 'src/main.py').write_text('from helper import value\n')
    (tmp_path / 'src/helper.py').write_text('value = 1\n')
    return tmp_path, snapshot(tmp_path)


def test_secondary_only_change_admits_complete_final_files(source):
    root, baseline = source
    (root / 'src/helper.py').write_text('value = 2\n')
    result = gate(root, baseline)
    assert result['accepted']
    assert result['changed_files'] == ['src/helper.py']


def test_addition_deletion_and_hidden_untracked_files_are_scoped(source):
    root, baseline = source
    (root / 'src/helper.py').unlink()
    (root / 'src/sibling.py').write_text('unauthorized')
    (root / '.hidden').write_text('untracked')
    result = gate(root, baseline)
    assert not result['accepted']
    assert result['changed_files'] == ['.hidden', 'src/helper.py', 'src/sibling.py']
    assert any('Missing required' in f['detail'] for f in result['failures'])


def test_authorized_deletion_of_nonrequired_file(source):
    root, baseline = source
    (root / 'src/helper.py').unlink()
    assert gate(root, baseline, required=['src/main.py'])['accepted']


def test_process_and_check_failures_cannot_be_bypassed(source):
    root, baseline = source
    result = gate(root, baseline, processes={'native': dict(OK, exit_code=17)},
                  checks={'frozen': dict(OK, exit_code=1)})
    assert not result['accepted']
    assert {f['group'] for f in result['failures']} == {'process/environment', 'behavior/review'}
    assert not gate(root, baseline, processes={})['accepted']
    assert not gate(root, baseline, checks={})['accepted']
    assert not gate(root, baseline, checks={'missing-shutdown': {'exit_code': 0}})['accepted']


def test_frozen_additions_and_drift_block_acceptance(source, tmp_path_factory):
    root, baseline = source
    frozen = tmp_path_factory.mktemp('freeze-parent') / 'v1'
    hashes = freeze({'test.py': b'assert 1 == 1\n'}, frozen)
    assert gate(root, baseline, frozen_root=frozen, frozen_hashes=hashes)['accepted']
    (frozen / 'unexpected.py').write_text('assert True')
    assert not gate(root, baseline, frozen_root=frozen, frozen_hashes=hashes)['accepted']
    (frozen / 'unexpected.py').unlink()
    (frozen / 'test.py').write_text('assert 1 == 2')
    assert not gate(root, baseline, frozen_root=frozen, frozen_hashes=hashes)['accepted']
    with pytest.raises(FileExistsError):
        freeze({'test.py': b'edited'}, frozen)


def test_review_blockers_and_environment_failure_block_acceptance(source):
    root, baseline = source
    assert not gate(root, baseline, review={'accepted': True, 'blockers': ['incompatible']})['accepted']
    assert not gate(root, baseline, review={})['accepted']
    assert not gate(root, baseline, environment_errors=['DB unavailable'])['accepted']


def test_symlink_is_rejected_without_reading_target(source, tmp_path_factory):
    root, baseline = source
    target = tmp_path_factory.mktemp('private') / 'secret'
    target.write_text('private canary')
    try:
        (root / 'src/link').symlink_to(target)
    except OSError:
        pytest.skip('Host cannot create symlinks; WSL live probe covers links')
    result = gate(root, baseline)
    assert not result['accepted']
    assert 'private canary' not in json.dumps(result)


def test_hardlinks_are_rejected(source):
    root, baseline = source
    try:
        os.link(root / 'src/main.py', root / 'src/copy.py')
    except OSError:
        pytest.skip('Host cannot create hardlinks; WSL covers this boundary')
    assert not gate(root, baseline)['accepted']


def test_failure_bytes_survive_cleanup_and_cannot_be_overwritten(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    root = workspace({'src/partial.py': b'def broken('})
    archive = tmp_path / 'rejected.zip'
    preserve(root, archive, {'workspace': str(root), 'exit_code': 17})
    with pytest.raises(FileExistsError):
        preserve(root, archive, {'workspace': str(root)})
    cleanup(root, preserved=archive)
    assert not root.exists()
    with zipfile.ZipFile(archive) as z:
        assert z.read('files/src/partial.py') == b'def broken('
        assert json.loads(z.read('outcome.json'))['exit_code'] == 17


def test_cleanup_refuses_unpreserved_changes_or_wrong_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    root = workspace({'src/file': b'first'})
    archive = tmp_path / 'before.zip'
    preserve(root, archive, {'workspace': str(root)})
    (root / 'src/file').write_bytes(b'later')
    with pytest.raises(ValueError, match='changed after preservation'):
        cleanup(root, preserved=archive)
    fresh = tmp_path / 'after.zip'
    preserve(root, fresh, {'workspace': str(root)})
    cleanup(root, preserved=fresh)


@pytest.mark.skipif(os.name != 'posix', reason='Linux-owned process group boundary')
def test_actual_exit_and_timeout_shutdown(tmp_path):
    failed = process([sys.executable, '-c', 'raise SystemExit(17)'], tmp_path)
    assert failed['exit_code'] == 17 and failed['owned_process_group_ended']
    timeout = process([sys.executable, '-c', 'import time; time.sleep(30)'], tmp_path, timeout=.1)
    assert timeout['timed_out'] and timeout['owned_process_group_ended']


@pytest.mark.skipif(os.name != 'posix', reason='Linux-owned process group boundary')
def test_a_surviving_descendant_is_killed_and_blocks_shutdown_success(tmp_path):
    code = ('import subprocess,sys; p=subprocess.Popen([sys.executable,"-c",'
            '"import time; time.sleep(60)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); '
            'print(p.pid,flush=True)')
    result = process([sys.executable, '-c', code], tmp_path)
    assert result['descendants_killed'] and not result['owned_process_group_ended']
    status = Path('/proc') / result['stdout'].strip() / 'status'
    for _ in range(50):
        if not status.exists() or '\nState:\tZ' in status.read_text():
            break
        time.sleep(.01)
    else:
        pytest.fail('Owned descendant remains live after group shutdown')


def test_worker_environment_drops_parent_agent_credentials(monkeypatch):
    for name in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'anthropic_auth_token',
                 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_OAUTH_TOKEN'):
        monkeypatch.setenv(name, 'secret')
    monkeypatch.setenv('KEEP_ME', 'value')
    child = environment()
    assert child['KEEP_ME'] == 'value'
    assert not {'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_AUTH_TOKEN',
                'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_OAUTH_TOKEN'} & {k.upper() for k in child}
