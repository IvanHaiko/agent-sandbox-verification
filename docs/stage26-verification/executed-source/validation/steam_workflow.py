"""Stage 25 native real-repository experiment; no alternate execution backend."""
import argparse
import ast
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import shutil
import tarfile
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

import jsonschema

from agent_system.artifacts import (archive, cleanup, digest, owned_workspace, require, save,
                                    snapshot, freeze_design, require_frozen)
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.roles import obj, TEXT, STRINGS, REVIEW_SCHEMA


def git(repository, *arguments):
    return subprocess.run(['git', '-C', str(repository), *arguments],
                          capture_output=True, check=True, timeout=30).stdout


def source_fingerprint(repository):
    """Include dirty/staged/untracked files without reading ignored data or credentials."""
    names = git(repository, 'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    files = {}
    for name in sorted(set(names.decode().split('\0')) - {''}):
        path = repository / name
        require(not path.is_symlink(), 'Linked original project file')
        files[name] = digest(path.read_bytes()) if path.is_file() else None
    return {'head': git(repository, 'rev-parse', 'HEAD').decode().strip(),
            'status': git(repository, 'status', '--porcelain=v1', '-uall').decode(),
            'index_diff_sha256': digest(git(repository, 'diff', '--cached', '--binary')),
            'working_diff_sha256': digest(git(repository, 'diff', '--binary')),
            'files': files}


def fixed_source(repository, commit):
    require(git(repository, 'rev-parse', commit + '^{commit}').decode().strip() == commit,
            'Source must be a full fixed commit')
    files = {}
    with tarfile.open(fileobj=io.BytesIO(git(repository, 'archive', commit))) as tar:
        for item in tar:
            name = PurePosixPath(item.name)
            require(not name.is_absolute() and '..' not in name.parts, 'Unsafe source path')
            require(item.isdir() or item.isfile(), 'Linked/nonregular source entry')
            if item.isfile():
                require(name.parts[0] != '.git', 'Source contains Git metadata')
                files[name.as_posix()] = tar.extractfile(item).read()
    return files


ARCHITECT_SCHEMA = obj({'interfaces': TEXT, 'approach': TEXT,
                        'timestamp_and_completeness_policy': TEXT,
                        'risks': STRINGS, 'test_environment': TEXT})


def validate_json(data, schema):
    value = json.loads(data)
    jsonschema.Draft202012Validator(schema).validate(value)
    return {'valid': True, 'schema_valid': True}


REQUIREMENTS = ['initial', 'replay', 'membership', 'rollback', 'hours', 'ordering',
                'invalid_or_incomplete', 'concurrency']
DESIGN_SCHEMA = obj({'cases': {'type': 'array', 'minItems': 8, 'items': obj({
    'requirement': {'type': 'string', 'enum': REQUIREMENTS}, 'test': TEXT, 'assertion': TEXT})},
    'limitations': STRINGS})


def project_candidate(files):
    require('src/load.py' in files and 'handoff/implementation.json' in files,
            'Implementation and handoff required')
    require('tests/test_twitch_hour_replacement.py' in files, 'Automated project tests required')
    for name, data in files.items():
        if name.endswith('.py'):
            ast.parse(data.decode())
    value = json.loads(files['handoff/implementation.json'])
    require(isinstance(value, dict) and 'summary' in value and 'tests' in value,
            'Handoff must record summary and tests')
    return {'valid': True, 'syntax_valid': True, 'handoff_valid': True}


def tester_artifacts(files):
    design = files.get('tests/test-design.json', b'{}')
    validate_json(design, DESIGN_SCHEMA)
    value = json.loads(design)
    require({c['requirement'] for c in value['cases']} == set(REQUIREMENTS),
            'Independent design omits a required category')
    source = files.get('tests/test_stage25_acceptance.py', b'')
    tree = ast.parse(source.decode())
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    require(len(names) >= 8 and {c['test'] for c in value['cases']} <= names,
            'Design test names must identify executable tests')
    return {'valid': True, 'schema_valid': True, 'test_functions': len(names)}


def acceptance_and_review(runner, directory, files, candidate, patch, canonical, freeze,
                          design, runtime, assessment, owned, db_env, *,
                          acceptance_module='test_stage25_acceptance', reviewer_focus=''):
    harness = (directory / 'frozen-acceptance.py').read_bytes()
    assessment['_active_stage'] = 'acceptance'
    require_frozen(directory, freeze)
    require({p: digest((directory / 'candidate' / p).read_bytes()) for p in candidate} ==
            {p: digest(b) for p, b in candidate.items()}, 'Candidate archive changed')
    acceptance_files = dict(files)
    workspace = owned_workspace(acceptance_files)
    owned.append(workspace)
    archive(workspace, 'implementation.patch', patch)
    git(workspace, 'apply', '--check', 'implementation.patch')
    git(workspace, 'apply', 'implementation.patch')
    (workspace / 'implementation.patch').unlink()
    require(all((workspace / p).read_bytes() == b for p, b in candidate.items()),
            'Patch did not reproduce candidate')
    assessment['patch_applies_to_fixed_source'] = True
    archive(workspace / 'tests', acceptance_module + '.py', harness)
    (workspace / 'scratch').mkdir()
    archive(workspace / 'scratch', '.keep', b'')
    exposure = {'exposed_at': time.time(), 'frozen_at': freeze['frozen_at'],
                'tester_session_running': False, 'candidate_sha256': digest(patch),
                'freeze_receipt_sha256': digest((directory / 'test-freeze.json').read_bytes())}
    require(exposure['exposed_at'] >= freeze['frozen_at'], 'Exposure preceded freeze')
    save(directory, 'candidate-exposure', exposure)
    before = snapshot(workspace)
    db_env['POSTGRES_TEST_DB'] = 'stage25_acceptance'
    db_env['TMPDIR'] = str(workspace / 'scratch')
    argv = ['/usr/bin/env', *[k + '=' + v for k, v in db_env.items()], runtime['python'],
            '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp=scratch/tmp',
            '--junitxml=scratch/results.xml', 'tests']
    result = runner.sandbox(workspace, argv, writable_directory='scratch', timeout=180,
                            database_socket_directory=runtime['socket'])
    archive(directory, 'acceptance-stdout.txt', result['stdout'].encode())
    archive(directory, 'acceptance-stderr.txt', result['stderr'].encode())
    junit = workspace / 'scratch/results.xml'
    independent = []
    if junit.exists():
        archive(directory, 'acceptance.xml', junit.read_bytes())
        independent = [t for t in ET.fromstring(junit.read_bytes()).iter('testcase')
                       if acceptance_module in t.get('classname', '')]
    require(result['owned_process_group_ended'] and not result['timed_out'],
            'Acceptance process failed shutdown/timeout boundary')
    shutil.rmtree(workspace / 'scratch')
    (workspace / 'scratch').mkdir()
    archive(workspace / 'scratch', '.keep', b'')
    require(snapshot(workspace) == before, 'Acceptance modified read-only project')
    require_frozen(directory, freeze)
    acceptance = {'returncode': result['exit_code'], 'model_requests': 0,
        'shutdown_confirmed': result['owned_process_group_ended'], 'timed_out': result['timed_out'],
        'independent_tests': len(independent), 'independent_passed': sum(len(t) == 0 for t in independent),
        'workspace_unchanged': True, 'network': 'separate user/network namespace; native filesystem sandbox; private database socket directory only; no host TCP or abstract IPC',
        'argv': argv, 'design_sha256': freeze['design_sha256'],
        'harness_sha256': freeze['harness_sha256'], 'patch_sha256': digest(patch)}
    save(directory, 'acceptance', acceptance)
    assessment['acceptance'] = acceptance
    assessment['acceptance_passed'] = result['exit_code'] == 0 and len(independent) >= 8 and all(
        len(t) == 0 for t in independent)
    require(len(independent) >= 8, 'Independent tests did not execute')
    cleanup(workspace)

    assessment['_active_stage'] = 'review'
    bundle = {'task': canonical, 'acceptance': acceptance,
        'test_design': design, 'implementation_handoff': json.loads((directory / 'implementer-handoff.json').read_text())}
    if acceptance_module != 'test_stage25_acceptance':
        bundle['compatibility_baseline'] = assessment.get('baseline_control')
        bundle['regression_controls'] = assessment.get('regression_controls')
    prompt = ('Role: Reviewer. Perform read-only review of this pinned repository with the candidate '
        'patch applied, candidate.patch, frozen test design and execution evidence in bundle.json, '
        'acceptance-stdout.txt, and tests/' + acceptance_module + '.py. Look for concrete correctness, '
        'data integrity, compatibility and maintainability defects. Consider acceptance failures even '
        'if the independent tests passed. Do not edit files, rerun tests, use network, credentials, '
        'other workspaces or subagents. Return only JSON matching schema.json through native '
        'structured output. An accept recommendation must have no blockers or blocking findings.\n'
        + reviewer_focus)
    review_files = dict(files)
    review_files.update(candidate)
    review_files.update({'role-input.md': prompt.encode(), 'TASK.json': json.dumps(canonical).encode(),
        'bundle.json': json.dumps(bundle, indent=2).encode(), 'schema.json': json.dumps(REVIEW_SCHEMA).encode(),
        'candidate.patch': patch, 'acceptance-stdout.txt': (directory / 'acceptance-stdout.txt').read_bytes(),
        'tests/' + acceptance_module + '.py': harness})
    workspace = owned_workspace(review_files)
    owned.append(workspace)
    archive(directory, 'reviewer-input.md', prompt.encode())
    review = NativeLinuxCodexRunner().run_read_only(trial_id=directory.name, role='reviewer', workspace=workspace,
        output=directory / 'reviewer-result.json', prompt=prompt,
        verify=lambda data: validate_json(data, REVIEW_SCHEMA), timeout=300)
    assessment['roles'].append(review)
    save(directory, 'reviewer-execution', review)
    require(review['execution_status'] == 'completed', 'Reviewer native/schema/scope failure')
    finding = json.loads((directory / 'reviewer-result.json').read_text())
    assessment['review'] = finding
    review_accepted = finding['recommendation'] == 'accept' and not finding['blockers'] and not any(
        f['severity'] == 'blocking' for f in finding['findings'])
    cleanup(workspace)
    review['cleanup_passed'] = True
    save(directory, 'reviewer-execution', review)
    require_frozen(directory, freeze)
    assessment['workflow_completed'] = True
    assessment['accepted'] = assessment['acceptance_passed'] and review_accepted
    if not assessment['accepted']:
        assessment['failure_category'] = 'acceptance_or_review_failed'


def run(args):
    directory, repository = args.evidence.resolve(), args.repository.resolve()
    prepared = json.loads((directory / 'architect-prepared.json').read_text())
    require(prepared['proposal_sha256'] == digest((directory / 'architect-result.json').read_bytes()),
            'Prepared Architect proposal changed')
    require(not (directory / 'assessment.json').exists(), 'Challenge already consumed; no retries')
    original = json.loads((directory / 'original-before.json').read_text())
    require(original == source_fingerprint(repository), 'Original changed after preparation')
    task = json.loads((directory / 'frozen-task.json').read_text())
    canonical = json.loads((directory / 'normalized-contract.json').read_text())
    require(all(canonical.get(k) == v for k, v in task.items()), 'Original task fields changed')
    normalization = json.loads((directory / 'contract-normalization.json').read_text())
    require(normalization['authority'] == 'Controller' and normalization['canonical_sha256'] ==
            digest((directory / 'normalized-contract.json').read_bytes()), 'Controller normalization missing')
    runtime = json.loads((directory / 'runtime.json').read_text())
    runner = NativeLinuxCodexRunner(read_paths=(str(Path(runtime['root']) / 'python'),))
    files = fixed_source(repository, args.commit)
    manifest = json.loads((directory / 'source-manifest.json').read_text())
    require(manifest['commit'] == args.commit and manifest['files'] ==
            {p: digest(b) for p, b in files.items()}, 'Pinned source changed')
    owned = []
    assessment = {'accepted': False, 'workflow_completed': False, 'outcome': 'FAIL',
        'roles': [json.loads((directory / 'architect-execution.json').read_text())],
        'started_at': json.loads((directory / 'preparation-assessment.json').read_text())['started_at'],
        'source_commit': args.commit, 'failure_category': None}
    stage = 'implementation'
    record = None

    def collect_role(role, workspace, prompt, target, allowed, verify, forbidden=(), timeout=600):
        nonlocal record
        owned.append(workspace)
        archive(directory, role + '-input.md', prompt.encode())
        role_runner = NativeLinuxCodexRunner() if role == 'independent_tester' else runner
        record = role_runner.run(trial_id=directory.name, role=role, workspace=workspace,
            target=target, prompt=prompt, verify=verify, forbidden_reads=forbidden,
            allowed_files=allowed, timeout=timeout)
        assessment['roles'].append(record)
        save(directory, role + '-execution', record)
        require(record['execution_status'] == 'completed', role + ' native/artifact/scope failure')
        return record

    def remove_role(workspace, role_record):
        cleanup(workspace)
        role_record['cleanup_passed'] = True
        save(directory, role_record['role'] + '-execution', role_record)

    try:
        db_env = {'POSTGRES_HOST': runtime['socket'], 'POSTGRES_PORT': '55425',
                  'POSTGRES_USER': 'stage25', 'POSTGRES_PASSWORD': 'disposable-local-only',
                  'POSTGRES_DB': 'stage25_unused', 'POSTGRES_TEST_DB': 'stage25_implementer',
                  'REQUIRE_DB_TESTS': '1', 'PYTHONDONTWRITEBYTECODE': '1',
                  'TMPDIR': 'tests/.stage25-tmp'}
        test_command = ['/usr/bin/env', *[k + '=' + v for k, v in db_env.items()], runtime['python'],
            '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp=tests/.stage25-tmp']
        prompt = ('Role: Implementer. Inspect the pinned real Python repository. Implement TASK.json '
            'independently; APPROACH.json is the Controller-approved Architect proposal. Preserve existing '
            'interfaces and make the smallest coherent changes. Only the project paths listed in '
            'controller_decisions.authorized_files and handoff/implementation.json may change. '
            'Run applicable non-database tests using the provided native Python runtime. '
            'Design database tests for Controller execution: the database socket is granted only to '
            'deterministic acceptance, not to model roles. This is an explicit capability boundary. '
            'Do not install packages, use project network, credentials, other workspaces, subagents or commits. '
            'Native temporary dirs are denied: pytest temporary files must use tests/.stage25-tmp. '
            'Delete that owned temporary test directory before ending; disable bytecode and pytest cache. '
            'Write handoff/implementation.json with summary, tests (commands/results), and limitations. '
            'The existing repository unit mocks may be updated in tests/test_load.py only as needed for '
            'the new public behavior; do not hide failures by skipping them. All other inputs and Git metadata '
            'are read-only. Controller independently freezes acceptance and evaluates your patch.\n'
            + 'Test command prefix (append selected test files): ' + json.dumps(test_command) + '\n')
        implementation_files = dict(files)
        implementation_files.update({'role-input.md': prompt.encode(),
            'TASK.json': json.dumps(canonical, indent=2).encode(),
            'APPROACH.json': (directory / 'architect-result.json').read_bytes(),
            'handoff/implementation.json': b'{}\n'})
        workspace = owned_workspace(implementation_files)
        allowed = canonical['controller_decisions']['authorized_files'] + ['handoff/implementation.json']
        impl = collect_role('implementer', workspace, prompt, 'src/load.py', allowed, project_candidate)
        candidate = {p: (workspace / p).read_bytes() for p in impl['changed_files']
                     if p != 'handoff/implementation.json'}
        for name, data in candidate.items():
            path = directory / 'candidate' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            archive(path.parent, path.name, data)
        save(directory, 'candidate-manifest', {p: digest(b) for p, b in candidate.items()})
        archive(directory, 'implementer-handoff.json', (workspace / 'handoff/implementation.json').read_bytes())
        # Controller stages only new authorized files to generate a standard applicable Git patch.
        new_files = [p for p in candidate if p not in files]
        if new_files:
            git(workspace, 'add', '--intent-to-add', '--', *new_files)
        patch = git(workspace, 'diff', '--no-ext-diff', '--binary', 'HEAD', '--', *candidate)
        archive(directory, 'steam-etl-implementation.patch', patch)
        assessment['patch_sha256'] = digest(patch)
        remove_role(workspace, impl)

        stage = 'test_design'
        # Deliberately omit Architect approach/risks/handoff and every src implementation.
        public_task = dict(task)
        public_task['controller_decisions'] = {k: v for k, v in canonical['controller_decisions'].items()
                                               if k != 'authorized_files'}
        prompt = ('Role: Independent Tester. Design meaningful acceptance independently from TASK.json '
            'and PUBLIC_INTERFACE.md. You receive no implementation, diff, Architect approach or handoff. '
            'Do not read any src tree, other workspaces, candidates, credentials, prior role histories, '
            'network or subagents. Write tests/test-design.json matching schema.json, with test names '
            'and behavioral assertions, plus executable tests/test_stage25_acceptance.py. These are the '
            'only mutable files. Each of the eight required categories must be represented. '
            'Use real PostgreSQL through the unchanged tests/conftest.py test_database fixture. '
            'Exercise public loader entry points and assert persisted complete observations. Include '
            'real transactional failure and bounded, synchronized concurrent same-hour execution. '
            'Do not use mocked SQL as the sole database evidence. You cannot execute against a candidate '
            'during this phase. Controller freezes both files after shutdown and executes them unchanged '
            'with the implementation later. Return no acceptance verdict now.\n')
        tester_files = {p: b for p, b in files.items()
                        if p.startswith('sql/') or p in ('tests/conftest.py', 'tests/__init__.py',
                            'tests/fixtures/twitch_streams.json', 'pytest.ini')}
        tester_files.update({'role-input.md': prompt.encode(),
            'TASK.json': json.dumps(public_task, indent=2).encode(),
            'PUBLIC_INTERFACE.md': canonical['controller_decisions']['public_interface'].encode(),
            'schema.json': json.dumps(DESIGN_SCHEMA).encode(), 'tests/test-design.json': b'{}\n',
            'tests/test_stage25_acceptance.py': b'# Blind acceptance artifact\n'})
        workspace = owned_workspace(tester_files)
        require(not (workspace / 'src').exists(), 'Tester received implementation')
        save(directory, 'tester-context', {'candidate_present': False, 'architect_approach_present': False,
            'handoff_present': False, 'files': sorted(tester_files), 'source_commit': args.commit})
        tester = collect_role('independent_tester', workspace, prompt, 'tests/test-design.json',
            ['tests/test-design.json', 'tests/test_stage25_acceptance.py'], tester_artifacts,
            [directory / 'candidate/src/load.py', directory / 'implementer-handoff.json',
             directory / 'architect-result.json', repository / 'src/load.py'])
        design_bytes = (workspace / 'tests/test-design.json').read_bytes()
        harness = (workspace / 'tests/test_stage25_acceptance.py').read_bytes()
        remove_role(workspace, tester)
        fixture = SimpleNamespace(TASK=task, strict_json=json.loads,
            validate_design=lambda data: validate_json(data, DESIGN_SCHEMA),
            acceptance_source=lambda design: harness.decode())
        freeze, _, design = freeze_design(directory, design_bytes, fixture)
        assessment['tester_candidate_blind_before_freeze'] = True
        assessment['independent_design_cases'] = len(design['cases'])

        stage = 'acceptance'
        acceptance_and_review(runner, directory, files, candidate, patch, canonical, freeze,
                              design, runtime, assessment, owned, db_env)
    except Exception as error:
        assessment.update(failed_stage=assessment.get('_active_stage', stage), failure_category='required_workflow_evidence_failed',
                          failure_type=type(error).__name__, failure_reason=str(error)[:1000])
    finally:
        failures = []
        for workspace in owned:
            if workspace.exists():
                try:
                    cleanup(workspace)
                except Exception as error:
                    failures.append(str(error))
        assessment['cleanup_passed'] = not failures and all(not p.exists() for p in owned)
        assessment['cleanup_failures'] = failures
        assessment['owned_workspaces'] = [str(p) for p in owned]
        after = source_fingerprint(repository)
        save(directory, 'original-after', after)
        assessment['original_unchanged'] = original == after
        assessment['accepted'] = assessment['accepted'] and assessment['cleanup_passed'] and original == after
        assessment['outcome'] = 'PASS' if assessment['accepted'] else 'FAIL'
        assessment['elapsed_seconds'] = round(time.time() - assessment['started_at'], 3)
        save(directory, 'controller-decision', {k: assessment[k] for k in
            ['accepted', 'outcome', 'cleanup_passed', 'original_unchanged', 'failure_category']})
        save(directory, 'assessment', assessment)
    print(json.dumps({k: v for k, v in assessment.items() if k not in ('roles', 'review')}, indent=2), flush=True)
    return 0 if assessment['accepted'] else 1


def prepare(args):
    directory = args.evidence.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    owned = []
    assessment = {'outcome': 'FAIL', 'accepted': False, 'roles': [],
                  'started_at': time.time(), 'failed_stage': 'prerequisites'}
    repository = args.repository.resolve()
    original = None
    try:
        original = source_fingerprint(repository)
        save(directory, 'original-before', original)
        files = fixed_source(repository, args.commit)
        save(directory, 'source-manifest', {'commit': args.commit,
             'files': {name: digest(data) for name, data in files.items()}})
        task = json.loads(args.contract.read_text(encoding='utf-8-sig'))
        save(directory, 'frozen-task', task)
        runner = NativeLinuxCodexRunner()
        assessment['codex_version'] = runner.version
        prompt = ('Role: Architect. Inspect the actual fixed source repository and TASK.json. '
            'Propose the smallest coherent Atomic Twitch Hour Replacement change. Identify '
            'public interfaces, timestamp types, complete versus incomplete bronze responses, '
            'ordering policy, transaction/concurrency risks, and available integration infrastructure. '
            'Do not edit project code or any input, use network, credentials, other workspaces or '
            'subagents. This workspace is read-only. Return JSON matching schema.json through '
            'native structured output. Controller approves the canonical contract.\n')
        files.update({'role-input.md': prompt.encode(), 'TASK.json': json.dumps(task).encode(),
                      'schema.json': json.dumps(ARCHITECT_SCHEMA).encode()})
        workspace = owned_workspace(files)
        owned.append(workspace)
        archive(directory, 'architect-input.md', prompt.encode())
        assessment['failed_stage'] = 'architect'
        record = runner.run_read_only(trial_id=directory.name, role='architect',
            workspace=workspace, output=directory / 'architect-result.json', prompt=prompt,
            verify=lambda data: validate_json(data, ARCHITECT_SCHEMA), timeout=300)
        assessment['roles'].append(record)
        save(directory, 'architect-execution', record)
        require(record['execution_status'] == 'completed', 'Architect native/schema/scope failure')
        assessment.update(outcome='PARTIAL', failed_stage=None, architect_completed=True)
        save(directory, 'architect-prepared', {'proposal_sha256':
             digest((directory / 'architect-result.json').read_bytes()), 'source_commit': args.commit})
    except Exception as error:
        assessment.update(failure_type=type(error).__name__, failure_reason=str(error)[:1000])
    finally:
        failures = []
        for workspace in owned:
            if workspace.exists():
                try:
                    cleanup(workspace)
                except Exception as error:
                    failures.append(str(error))
        assessment['cleanup_passed'] = not failures and all(not p.exists() for p in owned)
        assessment['cleanup_failures'] = failures
        assessment['owned_workspaces'] = [str(p) for p in owned]
        for record in assessment['roles']:
            record['cleanup_passed'] = not Path(record['workspace']).exists()
            save(directory, record['role'] + '-execution', record)
        if original is not None:
            after = source_fingerprint(repository)
            save(directory, 'original-after', after)
            assessment['original_unchanged'] = after == original
        assessment['elapsed_seconds'] = round(time.time() - assessment['started_at'], 3)
        save(directory, 'preparation-assessment', assessment)
    print(json.dumps({k: v for k, v in assessment.items() if k != 'roles'}, indent=2), flush=True)
    return 0 if assessment.get('architect_completed') and assessment['cleanup_passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run'])
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    return (prepare if args.mode == 'prepare' else run)(args)


if __name__ == '__main__':
    raise SystemExit(main())
