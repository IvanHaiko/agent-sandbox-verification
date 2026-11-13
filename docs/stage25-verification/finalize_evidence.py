"""Controller's final Stage 25 evidence audit; no model or target mutations."""
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from agent_system.artifacts import digest, require, save
from validation.steam_workflow import source_fingerprint


root = Path(__file__).resolve().parents[2]
directory = root / 'docs/stage25-verification/native-run'
repository = Path('/mnt/c/Users/4ivan/steam-etl')
before = json.loads((directory / 'original-before.json').read_text())
after = source_fingerprint(repository)
save(directory, 'original-after', after)
require(before == after, 'Original repository changed')
prepared = json.loads((directory / 'preparation-assessment.json').read_text())
architect = json.loads((directory / 'architect-execution.json').read_text())
runtime = json.loads((directory / 'runtime.json').read_text())
runtime_cleanup = json.loads((directory / 'runtime-cleanup.json').read_text())
postmaster_alive = Path('/proc', str(runtime['postmaster_pid'])).exists()
workspaces = prepared['owned_workspaces'] + [runtime['database_workspace']]
remaining = sorted(str(p) for p in Path.home().glob('codex-role-*'))
require(not remaining and all(not Path(p).exists() for p in workspaces), 'Owned workspace remains')
require(not postmaster_alive and all(runtime_cleanup.values()), 'Owned database/runtime remains')
suite = ET.parse(root / 'docs/stage25-verification/framework-final-wsl.xml').getroot()
require(all(s.get('failures') == '0' and s.get('errors') == '0' for s in suite.iter('testsuite')),
        'Framework regression failed')
profiles = [
    ('runtime-probe', 'network.enabled=false; runtime and socket directory read grants'),
    ('runtime-probe-scoped', 'network.enabled=false; exact PostgreSQL network.unix_sockets allow entry'),
    ('runtime-probe-proxy', 'network.enabled=true; native network proxy; domains {*: deny}; exact Unix socket'),
    ('runtime-probe-limited', 'network.enabled=true; native network proxy; mode=limited; empty domains; exact Unix socket'),
]
probes = []
for name, profile in profiles:
    value = json.loads((directory / (name + '.json')).read_text())
    require(value['exit_code'] != 0 and value['owned_process_group_ended'], 'Unexpected probe status')
    probes.append({'evidence': name + '.json', 'tested_profile': profile,
                   'exit_code': value['exit_code'], 'shutdown_confirmed': True})
assessment = {
    'outcome': 'FAIL', 'accepted': False, 'workflow_completed': False,
    'failed_stage': 'database_acceptance_prerequisite',
    'failure_category': 'native_database_sandbox_capability_not_demonstrated',
    'failure_reason': 'Healthy disposable PostgreSQL is inaccessible in every tested bounded native sandbox profile. Stopped before Implementer; no unsandboxed acceptance, broad-network fallback, model retries or additional agents.',
    'source_commit': before['head'], 'roles': [architect],
    'roles_not_executed': ['implementer', 'independent_tester', 'reviewer'],
    'functional_correctness': 'not evaluated; no candidate implementation',
    'code_quality': 'not evaluated; no Steam patch or independent review',
    'test_independence': 'not exercised; no Tester design, freeze or acceptance',
    'original_unchanged': before == after,
    'original_unchanged_checks': ['HEAD', 'status', 'staged binary diff', 'working binary diff',
                                  'tracked and nonignored untracked file hashes'],
    'patch_produced': False, 'patch_apply_check': 'not applicable',
    'framework_tests': {'passed': 37, 'failed': 0, 'errors': 0, 'skipped': 0},
    'database_diagnostic': 'Controller read-only SELECT succeeds outside sandbox; not acceptance',
    'sandbox_probes': probes,
    'cleanup_passed': True, 'owned_workspaces': workspaces,
    'remaining_role_workspaces': remaining, 'owned_postmaster_absent': not postmaster_alive,
    'runtime_cleanup': runtime_cleanup,
    'elapsed_seconds_from_native_preparation': round(time.time() - prepared['started_at'], 3),
    'native_model_seconds': architect['elapsed_seconds'],
    'model_consumption': 'unavailable; original native receipts did not retain token totals',
    'agent_model_route': 'gpt-6.1-sol / medium; one successful fresh ephemeral native context',
    'manual_interventions': ['Elevated WSL access required by desktop sandbox',
        'Controller added fixed-commit repository preparation and normalized Architect proposal',
        'Windows Docker started by user; WSL Docker integration unavailable',
        'Controller provisioned/extracted disposable PostgreSQL and pinned Python dependencies without system package installation',
        'Corrected PowerShell expansion in package extraction and empty owned-workspace input',
        'Tested documented native socket/proxy settings; retained each explicit failure',
        'Windows framework invocation failed on sandbox temporary-directory permissions; supported WSL suite passed',
        'Removed unsupported/unexecuted production extensions and stopped/removed disposable runtime'],
}
save(directory, 'assessment', assessment)
save(directory, 'controller-decision', {k: assessment[k] for k in
    ['outcome', 'accepted', 'workflow_completed', 'failure_category', 'cleanup_passed', 'original_unchanged']})
save(directory, 'evidence-manifest', {str(p.relative_to(directory)): digest(p.read_bytes())
    for p in directory.rglob('*') if p.is_file() and p.name != 'evidence-manifest.json'})
print(json.dumps({k: v for k, v in assessment.items() if k not in ('roles', 'manual_interventions')}, indent=2))
