"""Close out the explicitly authorized retry from existing receipts; no inference."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


def save(name, value):
    (OUT / (name + '.json')).write_text(json.dumps(value, indent=2))


record = load(OUT / 'architect/architect-1/architect-execution.json')
assert record['process_exit_code'] == 1 and record['cleanup_passed']
assert record['sandbox_preflight_passed'] and record['mutation_scope_valid']
assert record['shutdown_confirmed'] and not record['timed_out'] and not record['changed_files']
assert not Path(record['workspace']).exists()
assert not (OUT / 'architect/architect-1/architect-result.json').exists()
assert record['thread_id'] == '01a11698-9739-7733-866d-f9f471b63c58'
prior = load(OUT.parent / 'continuation/architect/architect-1/architect-execution.json')
assert prior['thread_id'] != record['thread_id'] and prior['workspace'] != record['workspace']
save('retry-decision', {'user_authorization': 'запускай повтор, потом полную цепочку, ели повтор пройдет',
    'retry_count_this_authorization': 1, 'retry_result': 'failed',
    'model': record['resolved_model'], 'reasoning': record['reasoning'],
    'native_thread': record['thread_id'], 'native_exit': record['process_exit_code'],
    'elapsed_seconds': record['elapsed_seconds'], 'required_artifact_present': False,
    'sandbox_preflight_passed': True, 'repository_unchanged': True,
    'process_shutdown_confirmed': True, 'cleanup_independently_verified': True,
    'failure_classification': 'unknown_native_runtime_failure',
    'diagnostic_limitation': 'Native error was multiline JSON; initial filter retained only ERROR: { prefixes. '
        'Native diagnostic store had no matching ERROR/WARN rows. Underlying native error is unavailable.',
    'future_diagnostic_fix': 'Parse complete native JSON error and retain message/type/code/param only; offline verified.',
    'corrected_diagnostics_live_verified': False,
    'full_chain_started': False, 'full_chain_condition_met': False,
    'additional_retry_started': False, 'stage24_started': False,
    'windows_sandbox_or_custom_transport_changed': False})
save('offline-checks', {'tests_run': 9, 'passed': True, 'failures': 0, 'errors': 0,
    'command': 'python3 -B -m unittest discover -s validation -p test_stage23*.py -v',
    'native_model_requests': 0, 'receipt_source': 'Controller observed unittest exit 0 / OK'})
save('baseline-reference', {'reviewer_gate_reused_without_live_restart': True,
    'source': '../continuation/reviewer/summary.json',
    'source_sha256': hashlib.sha256((OUT.parent / 'continuation/reviewer/summary.json').read_bytes()).hexdigest(),
    'copied_summary_sha256': hashlib.sha256((OUT / 'reviewer/summary.json').read_bytes()).hexdigest()})
assert (OUT.parent / 'continuation/reviewer/summary.json').read_bytes() == (OUT / 'reviewer/summary.json').read_bytes()
save('integrity-audit', {'passed': True, 'fresh_context_and_workspace': True,
    'failed_retry_repository_removed': True, 'required_architect_artifact_absent': True,
    'scope_unchanged': True, 'exact_model_requested': 'gpt-6.1-sol', 'effort': 'medium',
    'native_inference_response_confirmed': False,
    'executed_source_hashes': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in (OUT / 'architect').glob('*.py')}})
save('final-summary', {'verdict': 'STAGE23_PARTIAL_PASS',
    'preserved_gates': {'smoke': '3/3 PASS', 'minimal': '3/3 PASS', 'reviewer': '2/2 PASS'},
    'architect_workflows_completed': 0, 'architect_workflows_required': 2,
    'initial_architect_launch_result': 'failed', 'authorized_retry_result': 'failed',
    'total_failed_architect_launches': 2, 'full_chain_started': False,
    'failure_classification': 'unknown_native_runtime_failure',
    'failure_diagnostic_recovered': False, 'future_diagnostic_fix_offline_tests_passed': 9,
    'retry_cleanup_verified': True, 'additional_live_retry': False,
    'production_defaults_or_custom_transport_changed': False, 'stage24_started': False})
print('Retry closeout verified: failed, cleaned up, full-chain condition unmet')
