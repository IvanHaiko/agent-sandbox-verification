"""Controller audit of actual role, test, patch, source and cleanup evidence."""
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from agent_system.artifacts import digest, require, require_frozen, save
from validation.steam_workflow import source_fingerprint


directory = Path(__file__).resolve().parent
root = directory.parents[2]
assessment = json.loads((directory / 'assessment.json').read_text())
original = json.loads((directory / 'original-before.json').read_text())
after = source_fingerprint(Path('/mnt/c/Users/4ivan/steam-etl'))
require(original == after, 'Original repository changed')
save(directory, 'original-after', after)
freeze = json.loads((directory / 'test-freeze.json').read_text())
require_frozen(directory, freeze)
manifest = json.loads((directory / 'candidate-manifest.json').read_text())
require({p: digest((directory / 'candidate' / p).read_bytes()) for p in manifest} == manifest,
        'Candidate changed after review')
require(digest((directory / 'steam-etl-implementation.patch').read_bytes()) == assessment['patch_sha256'],
        'Patch changed after review')
require(assessment['patch_applies_to_fixed_source'], 'Patch application not established')
roles = assessment['roles']
require([r['role'] for r in roles] == ['architect', 'implementer', 'independent_tester', 'reviewer'],
        'Full role chain incomplete')
require(len({r['thread_id'] for r in roles}) == 4, 'Role contexts not distinct')
require(all(r['execution_status'] == 'completed' and r['resolved_model'] == 'gpt-6.1-sol'
            and r['shutdown_confirmed'] and r['cleanup_passed'] for r in roles), 'Role boundary failed')
runtime = json.loads((directory / 'runtime.json').read_text())
cleanup = json.loads((directory / 'runtime-cleanup.json').read_text())
require(all(cleanup.values()) and not Path('/proc', str(runtime['postmaster_pid'])).exists(),
        'Database process/runtime remains')
require(not list(Path.home().glob('codex-role-*')), 'Owned role workspace remains')
context = json.loads((directory / 'tester-context.json').read_text())
require(not context['candidate_present'] and not context['architect_approach_present']
        and not context['handoff_present'] and not any(p.startswith('src/') for p in context['files']),
        'Blind Tester context contaminated')
exposure = json.loads((directory / 'candidate-exposure.json').read_text())
require(exposure['exposed_at'] >= freeze['frozen_at'] and not exposure['tester_session_running'],
        'Freeze-before-exposure boundary failed')
cases = list(ET.parse(directory / 'acceptance.xml').getroot().iter('testcase'))
require(len(cases) == 234 and all(len(t) == 0 for t in cases), 'Acceptance not fully passing')
groups = {}
for case in cases:
    name = case.get('classname', '')
    groups[name] = groups.get(name, 0) + 1
independent = [t for t in cases if 'test_stage25_acceptance' in t.get('classname', '')]
require(len(independent) == 29, 'Independent suite missing')
baseline = json.loads((directory / 'baseline-control.json').read_text())
require(baseline['returncode'] == 1 and baseline['membership_defect_detected']
        and len(baseline['failures']) == 22, 'Meaningful negative control missing')
review = json.loads((directory / 'reviewer-result.json').read_text())
require(review['recommendation'] == 'accept' and not review['blockers'] and not review['findings'],
        'Review gate not accepted')
framework = list(ET.parse(directory / 'framework-final-wsl.xml').getroot().iter('testcase'))
require(len(framework) == 40 and all(len(t) == 0 for t in framework), 'Framework regressions failed')
audit = {'source_commit': assessment['source_commit'], 'original_unchanged': True,
    'candidate_unchanged_after_review': True, 'patch_sha256': assessment['patch_sha256'],
    'patch_applies_to_source': True, 'role_contexts_distinct': True,
    'tester_blindness_verified': True, 'freeze_before_exposure_verified': True,
    'acceptance': {'passed': 234, 'failed': 0, 'errors': 0, 'skipped': 0,
                   'independent_passed': 29, 'groups': groups},
    'negative_control': {'failed': 22, 'passed': 7, 'membership_defect_detected': True},
    'framework': {'passed': 40, 'failed': 0, 'errors': 0, 'skipped': 0},
    'cleanup_passed': True, 'owned_postmaster_absent': True,
    'remaining_role_workspaces': [], 'runtime_removed': True,
    'native_role_seconds': sum(r['elapsed_seconds'] for r in roles),
    'reported_tokens_available_roles': {r['role']: r['native_reported_tokens_used']
        for r in roles if 'native_reported_tokens_used' in r},
    'reported_tokens_partial_total': sum(r.get('native_reported_tokens_used', 0) for r in roles),
    'architect_tokens_unavailable': True, 'architect_reused_from_prior_attempt': True,
    'automatic_model_retries': 0, 'implementation_resamples': 0, 'tester_resamples': 0,
    'pytest_startup_failure_preserved': True, 'acceptance_environment_continuations': 1,
    'active_framework_sources': {p: digest((root / p).read_bytes()) for p in
        ['agent_system/native_codex_linux.py', 'validation/steam_workflow.py',
         'validation/steam_runtime.py', 'validation/steam_resume_acceptance.py',
         'validation/steam_negative_control.py', 'tests/test_native_launcher.py']}}
save(directory, 'final-integrity-audit', audit)
assessment.update(outcome='PASS', accepted=True, cleanup_passed=True, original_unchanged=True,
    acceptance_counts=audit['acceptance'], framework_counts=audit['framework'],
    negative_control=audit['negative_control'], database_runtime_cleanup=cleanup,
    final_audit_completed_at=time.time(), total_seconds_through_final_audit=round(time.time()-assessment['started_at'],3),
    limitations=['Table lock serializes all Twitch writers across hours',
        'Empty observations deliberately rejected; no durable watermark migration',
        'Unmarked upstream truncation cannot be detected in legacy bronze',
        'Implementer functional pytest startup was blocked; full Controller suite later passed',
        'Manual IPC/runtime/TMPDIR setup required; not a fully unattended run',
        'Architect token total unavailable; known role counters are partial and not billing estimates'])
save(directory, 'assessment', assessment)
save(directory, 'controller-decision', {'outcome': 'PASS', 'accepted': True,
    'workflow_completed': True, 'acceptance_passed': True, 'reviewer_recommendation': 'accept',
    'cleanup_passed': True, 'original_unchanged': True,
    'patch_sha256': assessment['patch_sha256'], 'source_commit': assessment['source_commit'],
    'basis': 'Frozen independent real PostgreSQL tests, full regressions, read-only review, negative control and final integrity audit'})
print(json.dumps(audit, indent=2))
