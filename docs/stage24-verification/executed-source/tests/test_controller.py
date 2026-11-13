"""Exercise real Controller handoff, freeze, acceptance and cleanup without model calls."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from agent_system import artifacts, controller
from validation import labels_contract as contract


def design():
    return {'task_id': contract.TASK_ID, 'contract_version': 1,
        'cases': [{'id': str(n), 'intent': 'Lowercase literal input', 'input': 'A' + str(n),
                   'expected': ['a' + str(n)]} for n in range(10)],
        'properties': ['unique_nonempty_labels', 'ascii_lowercase'], 'rationale': 'Offline fixture'}


class ArtifactRunner:
    def __init__(self, evidence, failure=None):
        self.evidence, self.failure = evidence, failure
        self.roles = []

    def run(self, *, role, workspace, target, verify, **kwargs):
        self.roles.append(role)
        if role == 'implementer':
            assert not (workspace / 'tests').exists()
            assert 'test-design' not in (workspace / 'TASK.json').read_text()
            data = b'def normalize_labels(value: str) -> list[str]:\n    return [value.lower()]\n'
        else:
            assert role == 'independent_tester'
            assert not (workspace / 'src').exists()
            assert not (self.evidence / 'test-freeze.json').exists()
            handoff = json.loads((self.evidence / 'implementer-handoff.json').read_text())
            assert handoff['authority'] == 'controller_observed_artifacts'
            assert not handoff['accepted']
            assert (self.evidence / 'candidate.py').exists()
            assert all(not Path(p).exists() for p in self.implementation_workspaces)
            assert len(kwargs['forbidden_reads']) == 2
            data = json.dumps(design()).encode()
        if self.failure == role:
            raise RuntimeError('Simulated native failure')
        (workspace / target).write_bytes(data)
        if role == 'implementer':
            self.implementation_workspaces = [str(workspace)]
        return {'workspace': str(workspace), 'execution_status': 'completed',
            'resolved_model': 'gpt-6.1-sol', 'thread_id': role, 'changed_files': [target],
            'diff': 'offline diff', 'artifact_check': verify(data)}

    def sandbox(self, workspace, argv, **kwargs):
        assert self.roles == ['implementer', 'independent_tester']
        freeze = json.loads((self.evidence / 'test-freeze.json').read_text())
        exposure = json.loads((self.evidence / 'candidate-exposure.json').read_text())
        assert exposure['sequence'] > freeze['sequence']
        assert exposure['exposed_at'] >= freeze['frozen_at']
        assert freeze['tester_execution_ended'] and not exposure['tester_session_running']
        artifacts.require_frozen(self.evidence, freeze)
        if self.failure == 'frozen_harness':
            (self.evidence / 'frozen-acceptance.py').write_text('changed after freeze')
        if self.failure == 'acceptance_scope':
            (workspace / 'TASK.json').write_text('mutated by test command')
        if self.failure == 'candidate_hash':
            (self.evidence / 'candidate.py').write_text('changed archived candidate')
        result = subprocess.run([sys.executable, '-I', '-B', '-c', argv[-1]],
            cwd=workspace, capture_output=True, text=True, timeout=10)
        return {'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr,
                'timed_out': False, 'owned_process_group_ended': True}


@pytest.fixture
def role_home(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('Owned Git workspace lifecycle runs inside the supported Linux/WSL backend')
    role_root = tmp_path / 'owned-role-home'
    role_root.mkdir()
    monkeypatch.setattr(Path, 'home', classmethod(lambda cls: role_root))
    return role_root


def test_minimal_workflow_accepts_artifacts_and_cleans_every_role(tmp_path, role_home):
    evidence = tmp_path / 'minimal'
    runner = ArtifactRunner(evidence)
    result = controller.run_workflow(runner, evidence, contract)
    assert result['accepted'] and result['cleanup_passed']
    assert result['case_count'] == 10
    assert runner.roles == ['implementer', 'independent_tester']
    assert len(result['owned_workspaces']) == 3
    assert not list(role_home.iterdir())
    decision = json.loads((evidence / 'controller-decision.json').read_text())
    assert decision['accepted'] and decision['cleanup_passed']


@pytest.mark.parametrize('failure', ['implementer', 'independent_tester', 'frozen_harness',
                                    'acceptance_scope', 'candidate_hash'])
def test_failures_stop_without_fallback_and_cleanup(tmp_path, role_home, failure):
    evidence = tmp_path / failure
    runner = ArtifactRunner(evidence, failure)
    result = controller.run_workflow(runner, evidence, contract)
    assert not result['accepted'] and result['failure_category']
    assert result['cleanup_passed'] and not list(role_home.iterdir())
    assert runner.roles.count('implementer') == 1  # failure never reroutes/retries


def test_optional_review_rejection_blocks_controller_acceptance(tmp_path, role_home):
    evidence = tmp_path / 'review-rejected'
    result = controller.run_workflow(ArtifactRunner(evidence), evidence, contract,
        review_hook=lambda *a: {'recommendation': 'reject'})
    assert result['acceptance']['result']['passed']
    assert not result['accepted']
    assert result['failure_category'] == 'reviewer_did_not_accept'
    assert result['cleanup_passed']


def test_cleanup_refuses_an_unowned_root(tmp_path):
    with pytest.raises(RuntimeError, match='Unsafe role cleanup root'):
        artifacts.cleanup(tmp_path)
    assert tmp_path.exists()


def test_snapshot_rejects_linked_artifact(tmp_path):
    target = tmp_path / 'target'
    target.write_text('input')
    (tmp_path / 'hardlink').hardlink_to(target)
    with pytest.raises(RuntimeError, match='Hard-linked workspace file'):
        artifacts.snapshot(tmp_path)


def test_freeze_checks_all_three_artifact_hashes(tmp_path):
    for name in ['frozen-test-design.json', 'frozen-acceptance.py', 'frozen-task.json']:
        directory = tmp_path / name
        directory.mkdir()
        artifacts.save(directory, 'frozen-task', contract.TASK)
        freeze, _, _ = artifacts.freeze_design(directory, json.dumps(design()).encode(), contract)
        (directory / name).write_text('changed')
        with pytest.raises(RuntimeError, match='changed'):
            artifacts.require_frozen(directory, freeze)
