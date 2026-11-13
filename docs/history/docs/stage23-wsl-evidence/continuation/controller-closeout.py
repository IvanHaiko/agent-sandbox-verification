"""Controller closeout from existing evidence only; no native invocation or retry."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'validation'))
import stage23_wsl_continuation as continuation
import stage23_wsl_workflow as flow

OUT = Path(__file__).resolve().parent


def load(path):
    return json.loads(path.read_text())


flow.require(load(OUT / 'integrity-audit.json')['passed'], 'Completed integrity audit required')
failed_dir = OUT / 'architect/architect-1'
record = load(failed_dir / 'architect-execution.json')
flow.require(record['process_exit_code'] == 1 and not (failed_dir / 'architect-result.json').exists(),
             'Failed Architect evidence required')
schema_bytes = json.dumps(continuation.ARCHITECT_SCHEMA, indent=2).encode()
flow.require(flow.digest(schema_bytes) == record['baseline_hashes']['schema.json'], 'Schema archive drift')
flow.archive(failed_dir, 'architect-output-schema.json', schema_bytes)
assessment = {'trial_id': 'architect-1', 'accepted': False, 'workflow_completed': False,
    'roles': [record], 'failed_stage': 'architect',
    'failure_category': 'unknown_native_runtime_failure',
    'failure_reason': 'Native exec exited 1 after 3.199 seconds without architect-result.json; stderr error not retained.',
    'native_error_text_available': False, 'inference_response_confirmed': False,
    'banner_model': record['resolved_model'], 'deterministic_setup_cause_confirmed': False,
    'cleanup_passed': record['cleanup_passed'], 'owned_workspaces': [record['workspace']],
    'cleanup_failures': [], 'automatic_retry_permitted_by_evidence': False,
    'record_authority': 'Controller closeout of original failed launch; no new native execution'}
flow.save(failed_dir, 'assessment', assessment)
flow.save(failed_dir, 'controller-decision', {'accepted': False,
    'source': 'Controller observed native exit and missing required Architect artifact',
    'failure_category': assessment['failure_category'], 'cleanup_passed': True,
    'later_roles_started': False, 'retry_started': False})
flow.save(OUT / 'architect', 'summary', {'required': 2, 'attempted': 1, 'accepted': 0,
    'gate': 'failed', 'trials': [assessment], 'unstarted_trials': ['architect-2'],
    'model': 'gpt-6.1-sol', 'reasoning': 'medium', 'cleanup_passed': True,
    'stop_reason': assessment['failure_reason'], 'retry_count': 0})
flow.save(OUT, 'offline-checks', {'passed': True, 'tests_run': 7, 'failures': 0, 'errors': 0,
    'command': 'python3 -B -m unittest discover -s validation -p test_stage23*.py -v',
    'native_model_requests': 0, 'receipt_source': 'Controller observed exit 0 and unittest OK'})
flow.save(OUT, 'native-diagnostic', {'command': 'codex doctor --json', 'exit_code': 0,
    'codex_version': '0.160.1', 'overall_status': 'warning',
    'checks': {'installation': 'ok', 'auth.credentials': 'ok', 'config.load': 'ok',
        'network.provider_reachability': 'ok', 'network.websocket_reachability': 'ok',
        'sandbox.helpers': 'ok', 'state.paths': 'ok', 'terminal.env': 'warning'},
    'warning': 'Non-interactive terminal reports 1x1 size.',
    'runtime_failure_cause_established': False,
    'receipt_source': 'Controller transcription of supported redacted diagnostic report',
    'credentials_read_copied_exported_by_controller': False,
    'native_inference_requested_by_controller': False})
flow.save(OUT, 'final-summary', {'verdict': 'STAGE23_PARTIAL_PASS',
    'smoke_gate': {'accepted': 3, 'required': 3, 'gate': 'passed', 'restarted': False},
    'minimal_gate': {'accepted': 3, 'required': 3, 'gate': 'passed', 'restarted': False},
    'reviewer_gate': {'accepted': 2, 'required': 2, 'gate': 'passed', 'frozen_cases_passed': 46},
    'architect_gate': {'accepted': 0, 'required': 2, 'attempted': 1, 'gate': 'failed'},
    'full_chain': {'accepted': 0, 'required': 1, 'attempted': 0, 'gate': 'not_started'},
    'stop_reason': assessment['failure_reason'], 'live_retry_count': 0,
    'stage24_started': False, 'production_defaults_changed': False,
    'custom_transport_changed': False, 'windows_permissions_changed': False,
    'new_native_successes': 6, 'new_failed_native_launches': 1,
    'new_removed_repositories': 9, 'integrity_audit_passed': True, 'offline_guard_tests_passed': 7})
print('Controller closeout saved: STAGE23_PARTIAL_PASS; no retries or later roles')
