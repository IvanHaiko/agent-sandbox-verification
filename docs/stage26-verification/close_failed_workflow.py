"""Complete deterministic candidate verification and the outstanding read-only review.

Independent design validation failed. This does not retry any completed role,
change the candidate, fabricate a freeze, or claim independent acceptance.
"""
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from agent_system.artifacts import archive, cleanup, digest, owned_workspace, require, save
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.roles import REVIEW_SCHEMA
from agent_system.test_environment import RoleTestEnvironment
from validation.steam_workflow import fixed_source, git, source_fingerprint, validate_json

directory = Path(__file__).resolve().parent
assessment = json.loads((directory / 'assessment.json').read_text())
require(assessment['failed_stage'] == 'test_design' and not assessment['accepted'], 'Unexpected closeout state')
require(not (directory / 'reviewer-execution.json').exists(), 'Reviewer already invoked')
original = json.loads((directory / 'original-before.json').read_text())
repository = Path('/mnt/c/Users/4ivan/steam-etl')
require(source_fingerprint(repository) == original, 'Original checkout changed')
files = fixed_source(repository, assessment['source_commit'])
manifest = json.loads((directory / 'candidate-manifest.json').read_text())
candidate = {p: (directory / 'candidate' / p).read_bytes() for p in manifest}
require(all(digest(b) == manifest[p] for p, b in candidate.items()), 'Candidate changed')
patch = (directory / 'steam-etl-implementation.patch').read_bytes()
canonical = json.loads((directory / 'normalized-contract.json').read_text())
require(canonical == json.loads((directory / 'frozen-task.json').read_text()), 'Frozen task changed')
runtime = json.loads((directory / 'runtime.json').read_text())
runner = NativeLinuxCodexRunner(read_paths=(Path(runtime['root']) / 'python',))
workspace = owned_workspace(files)
try:
    archive(workspace, 'candidate.patch', patch)
    git(workspace, 'apply', '--check', 'candidate.patch')
    git(workspace, 'apply', 'candidate.patch')
    (workspace / 'candidate.patch').unlink()
    require(all((workspace / p).read_bytes() == b for p, b in candidate.items()), 'Patch reproduction mismatch')
    (workspace / 'checks').mkdir()
    (workspace / 'checks/.keep').write_bytes(b'')
    service = RoleTestEnvironment(runner, runtime, directory, {'regression': ['pytest', 'tests']},
        database='stage26_controller_regression', evidence_prefix='controller-regression')
    service.workspace = workspace
    result = service.execute('regression')
    junit = directory / 'controller-regression-1.xml'
    cases = list(ET.parse(junit).iter('testcase'))
    verification = {'returncode': result['exit_code'], 'tests': len(cases),
        'failed': sum(t.find('failure') is not None for t in cases),
        'errors': sum(t.find('error') is not None for t in cases),
        'skipped': sum(t.find('skipped') is not None for t in cases),
        'patch_applies_to_fixed_source': True, 'candidate_reproduced_exactly': True,
        'patch_sha256': digest(patch), 'model_requests': 0,
        'independent_acceptance': 'NOT RUN: Tester design/harness rejected; no frozen executable artifacts'}
    save(directory, 'controller-regression', verification)
    require(result['exit_code'] == 0, 'Controller project regression failed')
finally:
    cleanup(workspace)

prompt = ('Role: Reviewer. Read-only review of the final candidate, TASK.json, candidate.patch and '
    'bundle.json. The experiment failed independent design validation; it has no frozen independent '
    'harness and no independent acceptance result. Do not treat project test success as that result. '
    'Evaluate concrete behavioral compatibility and engineering value: responsibilities/coupling, '
    'removed duplication, testability, readability, added abstractions, dependencies, and potential '
    'regressions. Identify code issues separately from missing experiment evidence. Frozen criterion 6 '
    'and full acceptance remain unmet. The supplied unchanged-component and exact source-hash checks '
    'are Controller evidence. Do not modify any files, rerun tests, read other workspaces, use '
    'network/credentials/subagents or propose weakening criteria. Return only schema.json structured '
    'output. State whether the refactoring itself has genuine engineering value while giving a '
    'recommendation appropriate to the incomplete acceptance evidence.')
bundle = {'task': canonical, 'implementation_handoff': json.loads((directory / 'implementer-handoff.json').read_text()),
    'controller_project_regression': verification, 'workflow_failure': assessment,
    'tester_failure': json.loads((directory / 'independent_tester-execution.json').read_text()),
    'independent_acceptance': {'status': 'NOT RUN', 'frozen_design': False, 'frozen_harness': False,
        'raw_rejected_artifacts_preserved': False, 'reason': 'Driver cleaned failed Tester workspace before archiving rejected outputs'},
    'unchanged_components': json.loads((directory / 'unchanged-components.json').read_text())}
review_files = dict(files)
review_files.update(candidate)
review_files.update({'TASK.json': json.dumps(canonical).encode(), 'role-input.md': prompt.encode(),
    'schema.json': json.dumps(REVIEW_SCHEMA).encode(), 'bundle.json': json.dumps(bundle, indent=2).encode(),
    'candidate.patch': patch})
workspace = owned_workspace(review_files)
try:
    archive(directory, 'reviewer-input.md', prompt.encode())
    record = NativeLinuxCodexRunner().run_read_only(trial_id=directory.name, role='reviewer',
        workspace=workspace, output=directory / 'reviewer-result.json', prompt=prompt,
        verify=lambda b: validate_json(b, REVIEW_SCHEMA), timeout=360)
    save(directory, 'reviewer-execution', record)
    require(record['execution_status'] == 'completed', 'Reviewer failed')
finally:
    cleanup(workspace)
    record['cleanup_passed'] = not workspace.exists()
    save(directory, 'reviewer-execution', record)
require(all(digest((directory / 'candidate' / p).read_bytes()) == h for p, h in manifest.items()), 'Candidate changed')
require(original == source_fingerprint(repository), 'Original changed')
save(directory, 'failed-workflow-closeout', {'candidate_unchanged': True, 'original_unchanged': True,
    'outstanding_reviewer_completed': True, 'project_regression': verification,
    'independent_acceptance_completed': False, 'automatic_retry': False,
    'purpose': 'Finish outstanding read-only review and deterministic patch verification without changing failed experiment outcome',
    'completed_at': time.time()})
print(json.dumps(verification, indent=2), flush=True)
