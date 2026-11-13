"""Save the observed native schema failure and its bounded Controller repair."""
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
failed_path = OUT.parent / 'continuation-diagnostic/architect/architect-2/architect-execution.json'
failed = json.loads(failed_path.read_text())
fixed = json.loads((OUT / 'architect/architect-2/architect-execution.json').read_text())
assert failed['process_exit_code'] == 1 and fixed['process_exit_code'] == 0
messages = [json.loads(line.partition(': ')[2]) for line in failed['native_error_diagnostics']]
assert all(e['code'] == 'invalid_json_schema' for e in messages)
assert fixed['execution_status'] == 'completed' and fixed['read_only'] and fixed['mutation_scope_valid']
assert fixed['baseline_hashes']['schema.json'] != failed['baseline_hashes']['schema.json']
receipt = {'confirmed_failure_classification': 'invocation/configuration: native output schema',
    'native_error': messages[0], 'failed_native_thread': failed['thread_id'],
    'failure_execution_sha256': hashlib.sha256(failed_path.read_bytes()).hexdigest(),
    'old_schema_sha256': failed['baseline_hashes']['schema.json'],
    'new_schema_sha256': fixed['baseline_hashes']['schema.json'],
    'repair': 'Remove array-valued const from native request schema; use scalar enums and fixed array '
        'lengths. Controller post-validation requires exact ordered lists for scope/criteria/constraints.',
    'task_scope_model_effort_sandbox_unchanged': True,
    'acceptance_criteria_exact_equality_preserved': True,
    'corrected_architect_thread': fixed['thread_id'], 'corrected_architect_role_passed': True,
    'targeted_guard': 'One Architect semantic guard, including changed scope/criteria and reordered/duplicated criteria.',
    'full_test_suite_run': False, 'old_successful_architect_workflow_reexecuted': False,
    'past_missing_error_limit': 'First two failed launches have no recoverable native error; '
        'the exact invalid_json_schema is established for the later failed Architect-2 launch only.'}
(OUT / 'schema-repair.json').write_text(json.dumps(receipt, indent=2))
baseline = {'reviewer_gate_source': '../continuation/reviewer/summary.json',
    'architect_1_source': '../continuation-diagnostic/architect/architect-1',
    'accepted_architect_1_reused_as_completed_workflow_evidence': True,
    'source_snapshots_preserved_in': 'architect/architect-1/executed-source',
    'successful_trials_restarted': False}
(OUT / 'baseline-reference.json').write_text(json.dumps(baseline, indent=2))
print('Schema repair receipt saved; exact native rejection and successful corrected Architect recorded')
