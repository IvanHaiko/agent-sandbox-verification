"""Three bounded native Implementer → blind Tester trials; stop on first failure."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_system.native_codex_linux import NativeLinuxCodexRunner, digest, snapshot
import stage23_labels_contract as contract

OUT = ROOT / 'docs/stage23-wsl-evidence/minimal'
TARGET = contract.TASK['file']
BASELINE = 'def normalize_labels(value: str) -> list[str]:\n    raise NotImplementedError\n'
DESIGN_TARGET = 'tests/test-design.json'


def save(directory, name, value):
    path = directory / (name + '.json')
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding='utf-8')
    return path


def require(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def owned_workspace(files):
    path = Path(tempfile.mkdtemp(prefix='stage23-flow-', dir=Path.home())).resolve()
    for name, data in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
    for args in (['init', '--initial-branch=main'], ['add', '.'],
            ['-c', 'user.name=Stage23 Controller', '-c', 'user.email=stage23@example.invalid',
             'commit', '-m', 'Freeze isolated role input']):
        subprocess.run(['git', '-C', str(path), *args], capture_output=True, timeout=15, check=True)
    return path


def cleanup(path):
    require(path.parent == Path.home().resolve() and path.name.startswith('stage23-flow-')
            and not path.is_symlink(), 'Unsafe role cleanup root')
    snapshot(path)
    shutil.rmtree(path)
    require(not path.exists(), 'Role cleanup failed')


def archive(directory, name, data):
    path = directory / name
    path.write_bytes(data)
    require(path.read_bytes() == data, 'Archive bytes mismatch')
    return path


def freeze_design(directory, design_bytes):
    contract.validate_design(design_bytes)
    design = contract.strict_json(design_bytes.decode())
    harness = contract.acceptance_source(design).encode('utf-8')
    ast.parse(harness.decode())
    archive(directory, 'frozen-test-design.json', design_bytes)
    archive(directory, 'frozen-acceptance.py', harness)
    receipt = {'design_sha256': digest(design_bytes), 'harness_sha256': digest(harness),
        'task_sha256': digest((directory / 'frozen-task.json').read_bytes()),
        'frozen_at': time.time(), 'sequence': 1, 'candidate_visible_during_design': False,
        'tester_execution_ended': True, 'tester_sessions': 1,
        'test_context_keys': ['task', 'public_interface', 'acceptance_criteria', 'constraints', 'schema']}
    save(directory, 'test-freeze', receipt)
    return receipt, harness, design


def require_frozen(directory, freeze):
    require(digest((directory / 'frozen-test-design.json').read_bytes()) == freeze['design_sha256'],
            'Frozen test design changed')
    require(digest((directory / 'frozen-acceptance.py').read_bytes()) == freeze['harness_sha256'],
            'Frozen acceptance harness changed')
    require(digest((directory / 'frozen-task.json').read_bytes()) == freeze['task_sha256'],
            'Frozen task changed')


def run_trial(runner, number):
    trial_id = 'minimal-' + str(number)
    directory = OUT / trial_id
    directory.mkdir()
    owned = []
    assessment = {'trial_id': trial_id, 'accepted': False, 'workflow_completed': False,
        'roles': [], 'failure_category': None, 'cleanup_passed': False}
    save(directory, 'frozen-task', contract.TASK)
    stage = 'implementation'
    task_text = json.dumps(contract.TASK, indent=2)
    try:
        implementer_input = ('Role: Implementer. Implement the frozen complete contract below.\n'
            'Read role-input.md, TASK.json and src/normalize_labels.py.\n'
            'Only src/normalize_labels.py may change. Preserve the exact typed public interface.\n'
            'No other files, imports with external dependencies, I/O, network, commits, subagents,\n'
            'other workspaces, credentials or previous role histories. No extra features.\n'
            'End immediately after the native file edit; no final summary is required.\n'
            'Controller derives the handoff and acceptance from artifacts, not your narration.\n'
            + task_text + '\n')
        implementation_workspace = owned_workspace({'role-input.md': implementer_input,
            'TASK.json': task_text, TARGET: BASELINE})
        owned.append(implementation_workspace)
        archive(directory, 'implementer-input.md', implementer_input.encode())
        record = runner.run(trial_id=trial_id, role='implementer', workspace=implementation_workspace,
            target=TARGET, prompt=implementer_input, verify=contract.validate_candidate)
        assessment['roles'].append(record)
        save(directory, 'implementer-execution', record)
        require(record['execution_status'] == 'completed', 'Implementer required artifact unavailable')
        candidate_bytes = (implementation_workspace / TARGET).read_bytes()
        candidate = archive(directory, 'candidate.py', candidate_bytes)
        candidate_hash = digest(candidate_bytes)
        assessment['candidate_sha256'] = candidate_hash
        handoff = {'role': 'implementer', 'execution_status': record['execution_status'],
            'model': record['resolved_model'], 'changed_files': record['changed_files'],
            'candidate_hashes': {TARGET: candidate_hash}, 'diff': record['diff'],
            'mutation_scope_valid': True, 'interface_check': record['artifact_check'],
            'candidate_status': 'unaccepted', 'accepted': False,
            'authority': 'controller_observed_artifacts'}
        save(directory, 'implementer-handoff', handoff)
        cleanup(implementation_workspace)
        record['cleanup_passed'] = True
        save(directory, 'implementer-execution', record)

        stage = 'test_design'
        tester_input = ('Role: Independent Tester. Read only role-input.md, TASK.json and schema.json.\n'
            'You receive the frozen task, public interface, acceptance criteria and supported domain.\n'
            'No candidate, implementation stub, diff, Implementer handoff, narration or history is supplied.\n'
            'Design 10-24 distinct deterministic ASCII-only cases covering ALL ten rules and their\n'
            'interactions: quote concatenation, comma/quote/backslash escaping in either mode, all\n'
            'six ASCII whitespace characters, ordinary versus protected boundaries and runs,\n'
            'lowercasing even quoted/escaped uppercase, deduplication, empty input, protected-only\n'
            'whitespace, trailing escape and unclosed quote after otherwise valid labels.\n'
            'expected must be a string list, or null for whole-input ValueError. Verify expectations\n'
            'against every rule. Unicode and non-string behavior are unspecified: never test them.\n'
            'Write ONLY tests/test-design.json as a JSON object matching schema.json.\n'
            'No executable test code, candidate access, other workspace, auth files, commits,\n'
            'network, dependencies or subagents. No other file may change.\n'
            'Your design is frozen and hashed before candidate exposure; Controller generates and\n'
            'runs the frozen harness. End after writing the artifact; no summary is required.\n'
            + task_text + '\n')
        tester_workspace = owned_workspace({'role-input.md': tester_input, 'TASK.json': task_text,
            'schema.json': json.dumps(contract.DESIGN_SCHEMA, indent=2), DESIGN_TARGET: '{}\n'})
        owned.append(tester_workspace)
        require(not (tester_workspace / 'src').exists(), 'Candidate or implementation stub visible to Tester')
        archive(directory, 'tester-input.md', tester_input.encode())
        save(directory, 'tester-context', {'candidate_present': False, 'src_present': False,
            'previous_conversation_visible': False, 'candidate_blindness': 'No src tree; native sandbox denies other role artifacts',
            'files': sorted(snapshot(tester_workspace)), 'input_sha256': digest(tester_input.encode())})
        record = runner.run(trial_id=trial_id, role='independent_tester', workspace=tester_workspace,
            target=DESIGN_TARGET, prompt=tester_input, verify=contract.validate_design,
            forbidden_reads=[candidate, directory / 'implementer-handoff.json'])
        assessment['roles'].append(record)
        save(directory, 'tester-execution', record)
        require(record['execution_status'] == 'completed', 'Tester required structured artifact unavailable')
        require(not (tester_workspace / 'src').exists(), 'Tester workspace contaminated with implementation')
        freeze, harness, design = freeze_design(directory, (tester_workspace / DESIGN_TARGET).read_bytes())
        assessment['frozen_tester_sha256'] = freeze['design_sha256']
        assessment['case_count'] = len(design['cases'])
        assessment['tester_candidate_blind_before_freeze'] = True
        cleanup(tester_workspace)
        record['cleanup_passed'] = True
        save(directory, 'tester-execution', record)

        stage = 'acceptance'
        require_frozen(directory, freeze)
        require(digest(candidate.read_bytes()) == candidate_hash, 'Candidate archive changed')
        acceptance_workspace = owned_workspace({TARGET: candidate.read_bytes(),
            'tests/controller_acceptance.py': harness, 'TASK.json': task_text})
        owned.append(acceptance_workspace)
        exposure = {'sequence': 2, 'exposed_at': time.time(), 'freeze_receipt_sha256':
            digest((directory / 'test-freeze.json').read_bytes()), 'candidate_sha256': candidate_hash,
            'recipient': 'Controller read-only acceptance sandbox', 'tester_session_running': False}
        require(exposure['exposed_at'] >= freeze['frozen_at'], 'Candidate exposed before freeze')
        save(directory, 'candidate-exposure', exposure)
        before_acceptance = snapshot(acceptance_workspace)
        result = runner.sandbox(acceptance_workspace,
            ['/usr/bin/python3', '-I', '-B', '-c', harness.decode()], timeout=30)
        require(result['owned_process_group_ended'] and not result['timed_out'], 'Acceptance process did not end safely')
        require(snapshot(acceptance_workspace) == before_acceptance, 'Acceptance changed frozen workspace')
        require_frozen(directory, freeze)
        require(digest(candidate.read_bytes()) == candidate_hash, 'Candidate changed during acceptance')
        output = contract.strict_json(result['stdout'].strip())
        require(output['passed'] == (result['exit_code'] == 0), 'Acceptance status disagrees with process')
        acceptance = {'model_requests': 0, 'tester_sessions': 0, 'returncode': result['exit_code'],
            'design_sha256': freeze['design_sha256'], 'harness_sha256': freeze['harness_sha256'],
            'candidate_sha256_before': candidate_hash, 'candidate_sha256_after': digest(candidate.read_bytes()),
            'mutation_scope_valid': True, 'result': output, 'executed_at': time.time(),
            'sandbox': 'native Linux Codex; read-only workspace; no project network'}
        save(directory, 'acceptance', acceptance)
        assessment['acceptance'] = acceptance
        if not output['passed']:
            assessment['classified_failures'] = contract.classify_failures(output, design)
            assessment['failure_category'] = 'frozen_acceptance_failed'
        assessment['workflow_completed'] = True
        assessment['accepted'] = bool(output['passed'])
        save(directory, 'controller-decision', {'accepted': assessment['accepted'],
            'candidate_sha256': candidate_hash, 'frozen_tester_sha256': freeze['design_sha256'],
            'source': 'Controller executed frozen independent tests', 'no_model_narration_dependency': True})
    except Exception as error:
        assessment['failed_stage'] = stage
        assessment['failure_category'] = assessment['failure_category'] or 'required_workflow_evidence_failed'
        assessment['failure_type'] = type(error).__name__
        assessment['failure_reason'] = str(error)[:1000]
    finally:
        failures = []
        for workspace in owned:
            if workspace.exists():
                try:
                    cleanup(workspace)
                except Exception as error:
                    failures.append(type(error).__name__)
        assessment['cleanup_passed'] = not failures and all(not path.exists() for path in owned)
        assessment['owned_workspaces'] = [str(path) for path in owned]
        assessment['cleanup_failures'] = failures
        assessment['accepted'] = assessment['accepted'] and assessment['cleanup_passed']
        save(directory, 'assessment', assessment)
    print(trial_id + ': ' + ('PASS' if assessment['accepted'] else 'FAIL'), flush=True)
    return assessment


def main():
    gate = json.loads((OUT.parent / 'smoke-summary.json').read_text(encoding='utf-8'))
    require(gate['gate'] == 'passed' and gate['usable'] == 3, 'Three-smoke prerequisite not passed')
    OUT.mkdir(exist_ok=False)
    archive(OUT, 'executed-driver.py', Path(__file__).read_bytes())
    archive(OUT, 'frozen-contract-and-harness.py', Path(contract.__file__).read_bytes())
    historical = json.loads((ROOT / 'docs/stage22-evidence/scoped-p1-t1/frozen-task.json').read_text())
    require(contract.TASK == historical, 'Previous acceptance contract changed')
    runner = NativeLinuxCodexRunner()
    summary = {'required': 3, 'accepted': 0, 'gate': 'running', 'trials': [],
        'model': 'gpt-6.1-sol', 'reasoning': 'medium', 'reviewer_started': False,
        'architect_started': False, 'no_transport_changes': True}
    save(OUT, 'summary', summary)
    for number in range(1, 4):
        assessment = run_trial(runner, number)
        summary['trials'].append(assessment)
        if assessment['accepted']:
            summary['accepted'] += 1
        save(OUT, 'summary', summary)
        if not assessment['accepted']:
            summary['stop_reason'] = assessment['failure_category']
            break
    sessions = [record['thread_id'] for trial in summary['trials'] for record in trial['roles']]
    summary['distinct_contexts'] = all(sessions) and len(sessions) == len(set(sessions))
    summary['cleanup_passed'] = all(trial['cleanup_passed'] for trial in summary['trials'])
    summary['gate'] = 'passed' if (summary['accepted'] == 3 and summary['distinct_contexts']
                                  and summary['cleanup_passed']) else 'failed'
    summary['native_role_executions'] = len(sessions)
    save(OUT, 'summary', summary)
    print(json.dumps({k: v for k, v in summary.items() if k != 'trials'}, indent=2), flush=True)


if __name__ == '__main__':
    main()
