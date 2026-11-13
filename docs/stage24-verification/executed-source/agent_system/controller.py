"""Validated native artifact workflow; Controller owns handoff, freeze and acceptance."""
import json
from pathlib import Path
import time

from .artifacts import (archive, cleanup, digest, freeze_design, owned_workspace,
                        require, require_frozen, save, snapshot)

DESIGN_TARGET = 'tests/test-design.json'


def run_workflow(runner, directory, contract, *, canonical_contract=None, initial_roles=(), review_hook=None):
    directory = Path(directory).resolve()
    trial_id = directory.name
    TARGET = contract.TASK['file']
    BASELINE = contract.BASELINE
    directory.mkdir(exist_ok=bool(initial_roles))
    require(not (directory / 'assessment.json').exists(), 'Trial already consumed')
    owned = [Path(record['workspace']) for record in initial_roles]
    assessment = {'trial_id': trial_id, 'accepted': False, 'workflow_completed': False,
        'roles': list(initial_roles), 'failure_category': None, 'cleanup_passed': False}
    save(directory, 'frozen-task', contract.TASK)
    stage = 'implementation'
    task_text = json.dumps(canonical_contract or contract.TASK, indent=2)
    try:
        implementer_input = ('Role: Implementer. Implement the frozen complete contract below.\n'
            'Read role-input.md, TASK.json and {TARGET}.\n'
            'Only {TARGET} may change. Preserve the exact typed public interface.\n'
            'No other files, imports with external dependencies, I/O, network, commits, subagents,\n'
            'other workspaces, credentials or previous role histories. No extra features.\n'
            'End immediately after the native file edit; no final summary is required.\n'
            'Controller derives the handoff and acceptance from artifacts, not your narration.\n'
            + task_text + '\n')
        implementer_input = implementer_input.replace('{TARGET}', TARGET)
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
        tester_input = contract.TESTER_INSTRUCTIONS + task_text + '\n'
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
        freeze, harness, design = freeze_design(directory, (tester_workspace / DESIGN_TARGET).read_bytes(), contract)
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
        if review_hook is not None and assessment['accepted']:
            stage = 'review'
            assessment['review'] = review_hook(runner, directory, assessment, owned,
                                               canonical_contract or contract.TASK, contract)
            assessment['accepted'] = (assessment['accepted'] and
                                     assessment['review']['recommendation'] == 'accept')
            if not assessment['accepted']:
                assessment['failure_category'] = 'reviewer_did_not_accept'
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
        save(directory, 'controller-decision', {'accepted': assessment['accepted'],
            'candidate_sha256': assessment.get('candidate_sha256'),
            'frozen_tester_sha256': assessment.get('frozen_tester_sha256'),
            'reviewer_recommendation': assessment.get('review', {}).get('recommendation'),
            'failure_category': assessment['failure_category'], 'cleanup_passed': assessment['cleanup_passed'],
            'source': 'Controller verified artifacts, frozen acceptance and optional Reviewer evidence'})
        save(directory, 'assessment', assessment)
    print(trial_id + ': ' + ('PASS' if assessment['accepted'] else 'FAIL'), flush=True)
    return assessment


