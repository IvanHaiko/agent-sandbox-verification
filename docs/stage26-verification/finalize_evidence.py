"""Final read-only artifact audit and metrics; no candidate edits or model calls."""
import ast
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from agent_system.artifacts import digest, require, require_frozen, save
from validation.steam_workflow import fixed_source, source_fingerprint


def counts(path):
    cases = list(ET.parse(path).iter('testcase'))
    return {'tests': len(cases), 'passed': sum(not any(t.find(tag) is not None
            for tag in ('failure', 'error', 'skipped')) for t in cases),
            **{name: sum(t.find(tag) is not None for t in cases) for name, tag in
               [('failed', 'failure'), ('errors', 'error'), ('skipped', 'skipped')]}}


directory = Path(__file__).resolve().parent
assessment = json.loads((directory / 'assessment.json').read_text())
manifest = json.loads((directory / 'candidate-manifest.json').read_text())
original = json.loads((directory / 'original-before.json').read_text())
current = source_fingerprint(Path('/mnt/c/Users/4ivan/steam-etl'))
candidate_hashes = {p: digest((directory / 'candidate' / p).read_bytes()) for p in manifest}
implementer = json.loads((directory / 'implementer-execution.json').read_text())
freeze = (json.loads((directory / 'test-freeze.json').read_text())
          if (directory / 'test-freeze.json').exists() else None)
if freeze is not None:
    require_frozen(directory, freeze)
normalization = json.loads((directory / 'contract-normalization.json').read_text())
require(normalization['canonical_sha256'] == digest((directory / 'normalized-contract.json').read_bytes()),
        'Canonical contract changed')
require(json.loads((directory / 'frozen-task.json').read_text()) ==
        json.loads((directory / 'normalized-contract.json').read_text()), 'Frozen task changed')
require(manifest == candidate_hashes and all(implementer['artifact_hashes'][p] == h
        for p, h in manifest.items()), 'Candidate provenance/hash mismatch')
checks = [json.loads(p.read_text()) for p in sorted(directory.glob('implementer-check-*.json'))]
final_checks = {}
for name in ('unit', 'integration', 'lint'):
    valid = [r for r in checks if r['check'] == name and r['exit_code'] == 0 and
             all(r['source_hashes'].get(p) == h for p, h in manifest.items())]
    require(valid, 'Final candidate lacks a successful ' + name + ' receipt')
    final_checks[name] = {'exit_code': 0, 'source_hashes_match_candidate': True}
runtime = json.loads((directory / 'runtime.json').read_text())
runtime_cleanup = json.loads((directory / 'runtime-cleanup.json').read_text())
require(runtime_cleanup['runtime_removed'] and runtime_cleanup['database_workspace_removed'],
        'Runtime not cleaned')
try:
    os.kill(runtime['postmaster_pid'], 0)
except ProcessLookupError:
    database_pid_absent = True
else:
    database_pid_absent = False
require(database_pid_absent, 'Owned PostgreSQL PID still exists')
roles = [json.loads((directory / (name + '-execution.json')).read_text()) for name in
         ('architect', 'implementer', 'independent_tester', 'reviewer')]
require(all(not Path(r['workspace']).exists() for r in roles), 'Role workspace remains')
exposure = (json.loads((directory / 'candidate-exposure.json').read_text())
            if (directory / 'candidate-exposure.json').exists() else None)
regression = json.loads((directory / 'controller-regression.json').read_text())
audit = {'original_unchanged': original == current, 'candidate_origin_implementer': True,
    'candidate_archive_unchanged': manifest == candidate_hashes,
    'patch_applies_to_fixed_source': regression['patch_applies_to_fixed_source'],
    'patch_sha256': digest((directory / 'steam-etl-implementation.patch').read_bytes()),
    'final_implementer_checks': final_checks, 'canonical_contract_unchanged': True,
    'independent_freeze_present': freeze is not None, 'independent_candidate_exposure_present': exposure is not None,
    'independent_acceptance': 'NOT RUN', 'rejected_tester_bytes_available': False,
    'all_role_workspaces_removed': True, 'postgresql_pid_absent': database_pid_absent,
    'runtime_removed': True, 'owned_role_directories_remaining': sorted(p.name for p in Path.home().glob('codex-role-*'))}
require(audit['original_unchanged'], 'Final integrity failed')
save(directory, 'final-integrity-audit', audit)
boundary = json.loads((directory / 'measurement-boundary.json').read_text())
metrics = {'role_invocations': len(roles), 'roles': [{k: r.get(k) for k in
    ('role', 'thread_id', 'elapsed_seconds', 'native_reported_tokens_used', 'resolved_model')} for r in roles],
    'role_seconds_total': round(sum(r['elapsed_seconds'] for r in roles), 3),
    'measured_stage_wall_seconds': round(time.time() - boundary['measured_stage_started_at'], 3),
    'wall_clock_boundary': boundary['boundary'], 'development_workflow_seconds': assessment['elapsed_seconds'],
    'native_reported_tokens_partial_total': sum(r.get('native_reported_tokens_used', 0) for r in roles),
    'billing_cost': None, 'counter_limit': 'Native reported counters only; no complete input/output/cache billing breakdown.',
    'user_interventions': 0, 'controller_manual_failure_closeouts': 1,
    'environment_startup_continuations': 0, 'automatic_role_retries': 0,
    'candidate_files_changed': sorted(manifest), 'candidate_source_files_changed': [p for p in manifest if p.startswith('src/')],
    'implementer_check_runs': len(checks), 'implementer_failed_check_runs': sum(r['exit_code'] != 0 for r in checks),
    'checks': {p.stem: counts(p) for p in directory.glob('*.xml')}}
save(directory, 'metrics', metrics)
source = fixed_source(Path('/mnt/c/Users/4ivan/steam-etl'), assessment['source_commit'])
def function_stats(data):
    tree = ast.parse(data.decode())
    selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in
                ('load_steam_store_file', '_load_steam_store_ok', '_load_steam_store_redirected', '_execute_steam_store_load')]
    return {'function_names': [n.name for n in selected],
            'record_persistence_call_sites': sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == 'load_transformed_record' for f in selected for n in ast.walk(f)),
            'conditionals_in_loader_functions': sum(isinstance(n, ast.If) for f in selected for n in ast.walk(f))}
quality = {'original_loader': function_stats(source['src/load.py']),
           'candidate_loader': function_stats((directory / 'candidate/src/load.py').read_bytes()),
           'interpretation_complexity': 'Outcome branching moved into pure preparation; semantic branching remains necessary, not eliminated.',
           'new_abstractions': 'One private frozen dataclass with four fields, three pure preparation functions, one effect executor; existing private adapters retained.',
           'new_dependencies': [], 'unchanged_existing_function_count': len(json.loads((directory / 'unchanged-components.json').read_text())['unchanged_functions']),
           'maintainability_basis': 'One metadata persistence sequence; preparation testable without I/O; ordered transaction effects centralized, identities and replay mark arguments explicit.',
           'costs': 'Private cross-module preparation imports and a shallow frozen result add indirection; preserved legacy partial-success and counter quirks remain.'}
save(directory, 'quality-comparison', quality)
print(json.dumps({'audit': audit, 'metrics': metrics, 'quality': quality}, indent=2))
