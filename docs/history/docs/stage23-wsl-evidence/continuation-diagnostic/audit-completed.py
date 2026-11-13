"""Read/hash completed workflow receipts only; no inference or test execution."""
import hashlib
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'validation'))
import stage23_wsl_continuation as continuation
import stage23_wsl_workflow as flow


def load(path):
    return flow.contract.strict_json(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


old_sessions = set()
for path in [OUT.parent / 'minimal/summary.json', OUT.parent / 'continuation/reviewer/summary.json']:
    for trial in load(path)['trials']:
        old_sessions.update(r['thread_id'] for r in trial['roles'])
old_sessions.update(r['thread_id'] for r in load(OUT.parent / 'smoke-summary.json')['trials'])
old_sessions.add(load(ROOT / 'docs/stage23b-evidence/isolated-home-workspace/smoke.json')['thread_id'])
for name in ['continuation', 'continuation-retry-1']:
    old_sessions.add(load(OUT.parent / name / 'architect/architect-1/architect-execution.json')['thread_id'])
sessions, workspaces, trials = [], [], []
for phase, number in [('architect', 1), ('architect', 2), ('full', 1)]:
    directory = OUT / phase / (phase + '-' + str(number))
    trial = load(directory / 'assessment.json')
    assert trial['accepted'] and trial['workflow_completed'] and trial['cleanup_passed']
    assert [r['role'] for r in trial['roles']] == ['architect', 'implementer', 'independent_tester', 'reviewer']
    for record in trial['roles']:
        assert record['resolved_model'] == record['model'] == 'gpt-6.1-sol'
        assert record['reasoning'] == 'medium' and record['process_exit_code'] == 0
        assert record['execution_status'] == 'completed' and record['fresh_context'] and record['ephemeral']
        assert not record['conversation_history_inherited'] and not record['timed_out']
        assert record['sandbox_preflight_passed'] and record['shutdown_confirmed'] and record['mutation_scope_valid']
        assert record['cleanup_passed'] and not Path(record['workspace']).exists()
        name = 'tester' if record['role'] == 'independent_tester' else record['role']
        assert sha(directory / (name + '-input.md')) == record['prompt_sha256']
        if record['role'] in ['architect', 'reviewer']:
            assert record['read_only'] and record['changed_files'] == []
            assert sha(directory / (name + '-result.json')) == record['artifact_sha256']
        else:
            expected = flow.TARGET if record['role'] == 'implementer' else flow.DESIGN_TARGET
            assert record['changed_files'] == [expected]
        sessions.append(record['thread_id'])
    workspaces.extend(trial['owned_workspaces'])
    canonical = load(directory / 'normalized-contract.json')
    assert all(canonical[k] == v for k, v in flow.contract.TASK.items())
    normalization = load(directory / 'contract-normalization.json')
    assert normalization['authority'] == 'Controller' and normalization['original_criteria_preserved']
    assert normalization['canonical_sha256'] == sha(directory / 'normalized-contract.json')
    assert normalization['proposal_sha256'] == sha(directory / 'architect-result.json')
    continuation.validate_semantic((directory / 'architect-result.json').read_bytes(), continuation.ARCHITECT_SCHEMA)
    continuation.validate_semantic((directory / 'reviewer-result.json').read_bytes(), continuation.REVIEW_SCHEMA)
    candidate_hash = sha(directory / 'candidate.py')
    assert candidate_hash == trial['candidate_sha256']
    handoff = load(directory / 'implementer-handoff.json')
    assert handoff['authority'] == 'controller_observed_artifacts'
    assert handoff['candidate_hashes'][flow.TARGET] == candidate_hash
    freeze = load(directory / 'test-freeze.json')
    flow.require_frozen(directory, freeze)
    exposure = load(directory / 'candidate-exposure.json')
    assert freeze['frozen_at'] <= exposure['exposed_at'] and freeze['sequence'] < exposure['sequence']
    assert not freeze['candidate_visible_during_design'] and freeze['tester_execution_ended']
    assert not exposure['tester_session_running'] and freeze['tester_sessions'] == 1
    assert exposure['freeze_receipt_sha256'] == sha(directory / 'test-freeze.json')
    assert exposure['candidate_sha256'] == candidate_hash
    design = load(directory / 'frozen-test-design.json')
    flow.contract.validate_design((directory / 'frozen-test-design.json').read_bytes())
    assert (directory / 'frozen-acceptance.py').read_bytes() == flow.contract.acceptance_source(design).encode()
    acceptance = load(directory / 'acceptance.json')
    assert acceptance['model_requests'] == acceptance['tester_sessions'] == acceptance['returncode'] == 0
    assert acceptance['result']['passed'] and acceptance['mutation_scope_valid']
    assert acceptance['candidate_sha256_before'] == acceptance['candidate_sha256_after'] == candidate_hash
    assert acceptance['design_sha256'] == freeze['design_sha256']
    assert acceptance['harness_sha256'] == freeze['harness_sha256']
    assert len(acceptance['result']['cases']) == len(design['cases']) == trial['case_count']
    assert all(case['passed'] for case in acceptance['result']['cases'])
    assert all(prop['passed'] for prop in acceptance['result']['properties'])
    for case in design['cases']:
        try:
            expected = flow.contract.contract_interpret(case['input'])
        except ValueError:
            expected = None
        assert expected == case['expected']
    decision = load(directory / 'controller-decision.json')
    assert decision['accepted'] and decision['cleanup_passed'] and decision['reviewer_recommendation'] == 'accept'
    review = load(directory / 'reviewer-result.json')
    assert review['recommendation'] == 'accept'
    marginal = load(directory / 'reviewer-marginal-value.json')
    marginal.update(controller_evaluation_pending=False,
        controller_novel_material_findings=sum(not f['already_established_by_acceptance'] for f in review['findings']),
        controller_decision_changed=False)
    flow.save(directory, 'reviewer-marginal-value', marginal)
    trials.append({'trial_id': trial['trial_id'], 'case_count': trial['case_count'],
        'canonical_original_contract_unchanged': True, 'candidate_and_frozen_hashes_verified': True,
        'freeze_preceded_exposure': True, 'frozen_expectations_contract_consistent': True,
        'readonly_architect_and_reviewer': True, 'cleanup_independently_verified': True})
assert len(sessions) == len(set(sessions)) == 12 and not set(sessions) & old_sessions
assert len(workspaces) == len(set(workspaces)) == 15 and all(not Path(p).exists() for p in workspaces)
source_hashes = {}
for phase in ['architect', 'full']:
    source_hashes[phase] = {}
    for name, source in [('executed-driver.py', Path(continuation.__file__)),
                         ('workflow-driver.py', Path(flow.__file__)),
                         ('native-runner.py', ROOT / 'agent_system/native_codex_linux.py'),
                         ('contract-harness.py', Path(flow.contract.__file__))]:
        assert (OUT / phase / name).read_bytes() == source.read_bytes()
        source_hashes[phase][name] = sha(source)
original_schema_hash = load(OUT.parent / 'continuation/architect/architect-1/architect-execution.json')['baseline_hashes']['schema.json']
assert load(OUT / 'architect/architect-1/architect-execution.json')['baseline_hashes']['schema.json'] == original_schema_hash
flow.save(OUT, 'integrity-audit', {'passed': True, 'trials': trials,
    'distinct_successful_native_contexts': 12, 'distinct_from_all_prior_successes_and_failures': True,
    'all_fifteen_new_repositories_removed': True, 'original_architect_schema_unchanged': True,
    'total_frozen_cases': sum(t['case_count'] for t in trials), 'executed_source_hashes': source_hashes,
    'audit_model_requests': 0, 'audit_test_executions': 0, 'full_test_suite_run': False})
print('Completed-workflow receipts/hash audit PASS; no inference or test execution')
