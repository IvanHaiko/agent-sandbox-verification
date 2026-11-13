"""One Stage 26 refactoring experiment through the existing native WSL chain."""
import argparse
import ast
import json
from pathlib import Path
import shutil
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

from agent_system.artifacts import (archive, cleanup, digest, freeze_design, owned_workspace,
                                    require, require_frozen, save, snapshot)
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.roles import obj, TEXT, STRINGS
from agent_system.test_environment import RoleTestEnvironment
from validation.steam_workflow import (fixed_source, git, source_fingerprint, validate_json,
                                        acceptance_and_review)


ARCHITECT_SCHEMA = obj({'problem': TEXT, 'affected_components': STRINGS, 'public_interfaces': TEXT,
    'unchanged_behavior': STRINGS, 'expected_improvement': TEXT, 'approach': TEXT,
    'risks': STRINGS, 'authorized_files': STRINGS, 'proposed_acceptance_criteria': STRINGS})
REQUIREMENTS = ['interfaces', 'success', 'empty', 'ordering', 'errors', 'transactions',
                'persistence', 'unrelated_behavior']
DESIGN_SCHEMA = obj({'cases': {'type': 'array', 'minItems': 8, 'items': obj({
    'requirement': {'type': 'string', 'enum': REQUIREMENTS}, 'test': TEXT, 'assertion': TEXT})},
    'limitations': STRINGS})


def prepare(args):
    directory = args.evidence.resolve()
    require(not (directory / 'architect-execution.json').exists(), 'Architect already invoked')
    repository = args.repository.resolve()
    original = source_fingerprint(repository)
    save(directory, 'original-before', original)
    files = fixed_source(repository, args.commit)
    save(directory, 'source-manifest', {'commit': args.commit,
        'files': {p: digest(b) for p, b in files.items()}})
    task = {'mission': 'Select one useful bounded Python ETL refactoring affecting at least two related '
            'functions or modules. Preserve current observable behavior and public interfaces. '
            'Inspect actual source/tests; no business feature, cosmetic-only change, broad rewrite, '
            'dependency upgrade or migration. Explain concrete duplication/coupling and improvement.',
            'source_commit': args.commit}
    prompt = ('Role: Architect. Inspect the pinned source and existing tests. Select and propose one '
        'real maintainability refactoring for TASK.json. You choose the opportunity based on actual '
        'code. List affected functions/modules, allowed files, unchanged behavior and plausible '
        'regressions. Prefer a bounded loading/transformation pipeline separation with meaningful '
        'unit and PostgreSQL validation. Preserve even awkward legacy semantics. Do not implement '
        'or edit any file, use network, credentials, other workspaces or subagents. Return only '
        'schema.json structured output. Controller approves a specific contract before implementation.')
    files.update({'TASK.json': json.dumps(task).encode(), 'role-input.md': prompt.encode(),
                  'schema.json': json.dumps(ARCHITECT_SCHEMA).encode()})
    workspace = owned_workspace(files)
    try:
        archive(directory, 'architect-input.md', prompt.encode())
        record = NativeLinuxCodexRunner().run_read_only(trial_id=directory.name, role='architect',
            workspace=workspace, output=directory / 'architect-result.json', prompt=prompt,
            verify=lambda b: validate_json(b, ARCHITECT_SCHEMA), timeout=360)
        save(directory, 'architect-execution', record)
        require(record['execution_status'] == 'completed', 'Architect failed')
    finally:
        cleanup(workspace)
        save(directory, 'preparation-integrity', {'original_unchanged': original == source_fingerprint(repository),
                                                 'workspace_removed': not workspace.exists()})
    save(directory, 'architect-prepared', {'proposal_sha256':
         digest((directory / 'architect-result.json').read_bytes()), 'source_commit': args.commit})


def candidate_valid(files):
    require('handoff/implementation.json' in files and any(p.startswith('src/') for p in files),
            'Code and handoff required')
    require('tests/test_refactoring.py' in files, 'Implementer regression tests required')
    for p, b in files.items():
        if p.endswith('.py'):
            ast.parse(b.decode())
    handoff = json.loads(files['handoff/implementation.json'])
    require('summary' in handoff and 'tests' in handoff, 'Handoff must record checks')
    return {'valid': True, 'syntax_valid': True}


def tester_valid(files):
    value = json.loads(files.get('tests/test-design.json', b'{}'))
    validate_json(json.dumps(value), DESIGN_SCHEMA)
    require({c['requirement'] for c in value['cases']} == set(REQUIREMENTS), 'Missing regression category')
    tree = ast.parse(files.get('tests/test_stage26_acceptance.py', b'').decode())
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    require(len(names) >= 8 and {c['test'] for c in value['cases']} <= names, 'Design/harness mismatch')
    return {'valid': True, 'test_functions': len(names)}


def preserve_components(files, candidate):
    """Require all existing functions outside the frozen refactoring scope unchanged."""
    allowed = {'src/load.py': {'load_steam_store_file', '_load_steam_store_ok', '_load_steam_store_redirected'},
               'src/transform.py': set()}
    checked = []
    for path, permitted in allowed.items():
        old = ast.parse(files[path].decode())
        new = ast.parse(candidate.get(path, files[path]).decode())
        functions = {n.name: ast.dump(n) for n in new.body if isinstance(n, ast.FunctionDef)}
        for node in old.body:
            if isinstance(node, ast.FunctionDef) and node.name not in permitted:
                require(functions.get(node.name) == ast.dump(node), 'Unrelated function changed: ' + node.name)
                checked.append(path + ':' + node.name)
    return {'unchanged_functions': checked, 'persistence_sql_unchanged': True}


def run(args):
    directory, repository = args.evidence.resolve(), args.repository.resolve()
    require(not (directory / 'assessment.json').exists(), 'Experiment already consumed; no retry')
    prepared = json.loads((directory / 'architect-prepared.json').read_text())
    require(prepared['proposal_sha256'] == digest((directory / 'architect-result.json').read_bytes()),
            'Architect changed')
    task = json.loads((directory / 'frozen-task.json').read_text())
    canonical = json.loads((directory / 'normalized-contract.json').read_text())
    require(task == canonical, 'Frozen contract mismatch')
    normalization = json.loads((directory / 'contract-normalization.json').read_text())
    require(normalization['authority'] == 'Controller' and normalization['canonical_sha256'] ==
            digest((directory / 'normalized-contract.json').read_bytes()), 'Contract approval missing')
    original = json.loads((directory / 'original-before.json').read_text())
    require(original == source_fingerprint(repository), 'Original changed')
    files = fixed_source(repository, args.commit)
    require(json.loads((directory / 'source-manifest.json').read_text())['files'] ==
            {p: digest(b) for p, b in files.items()}, 'Source changed')
    runtime = json.loads((directory / 'runtime.json').read_text())
    runner = NativeLinuxCodexRunner(read_paths=(Path(runtime['root']) / 'python',))
    assessment = {'accepted': False, 'workflow_completed': False, 'outcome': 'FAIL',
                  'source_commit': args.commit, 'started_at': time.time(), 'failure_category': None,
                  'roles': [json.loads((directory / 'architect-execution.json').read_text())]}
    owned, stage = [], 'implementation'
    def remove(workspace, record):
        cleanup(workspace)
        record['cleanup_passed'] = True
        save(directory, record['role'] + '-execution', record)
    try:
        prompt = ('Role: Implementer. Implement only the approved maintainability refactoring in '
            'TASK.json; APPROACH.json is the approved proposal. Preserve public interfaces, data '
            'semantics, error/print behavior and transaction boundaries. Only authorized_files and '
            'handoff/implementation.json may change. Do not alter existing tests, migrations or '
            'dependencies. Add focused tests/test_refactoring.py. No unnecessary abstractions. '
            'A working Controller-provisioned test facility is available: run /usr/bin/python3 -B '
            'controller-check.py unit, then integration, then lint. These named checks execute '
            'your current candidate in the native filesystem sandbox and a private network namespace '
            'against disposable PostgreSQL. The model retains network disabled; do not invoke codex, '
            'set up infrastructure, install packages, use network/credentials/other workspaces, '
            'subagents or commits. Wait for each check. Fix your own failures before handoff; no '
            'skips or weakened expectations. Record exact commands/results and refactoring value in '
            'handoff/implementation.json with summary, tests, compatibility, quality and limitations. '
            'Controller validates the final candidate hashes against successful check receipts.')
        implementation = dict(files)
        implementation.update(RoleTestEnvironment.inputs())
        implementation.update({'TASK.json': json.dumps(task, indent=2).encode(), 'role-input.md': prompt.encode(),
            'APPROACH.json': (directory / 'architect-result.json').read_bytes(),
            'handoff/implementation.json': b'{}\n'})
        workspace = owned_workspace(implementation)
        owned.append(workspace)
        checks = {'unit': ['pytest', *task['unit_test_files'], 'tests/test_refactoring.py'],
                  'integration': ['pytest', 'tests'],
                  'lint': ['ruff', *[p for p in task['authorized_files'] if p.endswith('.py')]]}
        service = RoleTestEnvironment(runner, runtime, directory, checks, database='stage26_implementer')
        archive(directory, 'implementer-input.md', prompt.encode())
        impl = runner.run(trial_id=directory.name, role='implementer', workspace=workspace,
            target=task['primary_file'], allowed_files=task['authorized_files'] + ['handoff/implementation.json'],
            prompt=prompt, verify=candidate_valid, timeout=900, test_environment=service)
        assessment['roles'].append(impl)
        save(directory, 'implementer-execution', impl)
        # Preserve produced artifacts even if native validation fails.
        candidate = {p: (workspace / p).read_bytes() for p in impl.get('changed_files', [])
                     if p in task['authorized_files'] and (workspace / p).is_file()}
        for p, b in candidate.items():
            path = directory / 'candidate' / p
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b)
        save(directory, 'candidate-manifest', {p: digest(b) for p, b in candidate.items()})
        archive(directory, 'implementer-handoff.json', (workspace / 'handoff/implementation.json').read_bytes())
        new_files = [p for p in candidate if p not in files]
        if new_files:
            git(workspace, 'add', '--intent-to-add', '--', *new_files)
        patch = git(workspace, 'diff', '--no-ext-diff', '--binary', 'HEAD', '--', *candidate)
        archive(directory, 'steam-etl-implementation.patch', patch)
        require(impl['execution_status'] == 'completed', 'Implementer native/artifact/scope failure')
        save(directory, 'unchanged-components', preserve_components(files, candidate))
        for check in ('unit', 'integration', 'lint'):
            require(any(r['check'] == check and r['exit_code'] == 0 and
                        all(r['source_hashes'].get(p) == digest(b) for p, b in candidate.items())
                        for r in service.results), 'No successful final-candidate ' + check + ' check')
        assessment['implementer_test_execution_passed'] = True
        remove(workspace, impl)

        stage = 'test_design'
        public = {k: task[k] for k in ('mission', 'source_commit', 'public_interface', 'behavior_contract',
                                      'acceptance_criteria', 'constraints')}
        prompt = ('Role: blind Independent Tester. Establish behavior only from TASK.json and '
            'PUBLIC_INTERFACE.md, the unchanged PostgreSQL fixture/schema and authorized public '
            'interfaces. No candidate, diff, Implementer handoff, Architect approach or src tree is '
            'provided or permitted. Independently design regression/adversarial tests for the '
            'eight schema categories. Write only tests/test-design.json and '
            'tests/test_stage26_acceptance.py. Cover exact outputs/counts/messages/errors, ordering, '
            'empty input, transaction boundaries, rollback and real PostgreSQL persistence where '
            'applicable. Avoid encoding private helper names or the refactoring approach. Use '
            'existing test_database fixture for real DB tests; no SQL mocks as sole persistence '
            'evidence. Tests must also pass the unchanged fixed-source implementation: this is '
            'behavior preservation. Controller freezes both artifacts after shutdown, executes '
            'unchanged on baseline and candidate and may apply deliberate regression controls. '
            'No network, credentials, other workspaces, src reads, subagents or candidate execution. '
            'Return no acceptance verdict now.')
        tester_files = {p: b for p, b in files.items() if p.startswith('sql/') or
                        p in ('tests/conftest.py', 'tests/__init__.py', 'pytest.ini')}
        tester_files.update({'TASK.json': json.dumps(public, indent=2).encode(), 'role-input.md': prompt.encode(),
            'PUBLIC_INTERFACE.md': task['public_interface'].encode(), 'schema.json': json.dumps(DESIGN_SCHEMA).encode(),
            'tests/test-design.json': b'{}\n', 'tests/test_stage26_acceptance.py': b'# Blind harness\n'})
        workspace = owned_workspace(tester_files)
        owned.append(workspace)
        save(directory, 'tester-context', {'files': sorted(tester_files), 'candidate_present': False,
              'approach_present': False, 'handoff_present': False, 'source_commit': args.commit})
        archive(directory, 'independent_tester-input.md', prompt.encode())
        tester = NativeLinuxCodexRunner().run(trial_id=directory.name, role='independent_tester',
            workspace=workspace, target='tests/test-design.json', prompt=prompt, verify=tester_valid,
            allowed_files=['tests/test-design.json', 'tests/test_stage26_acceptance.py'], timeout=900,
            forbidden_reads=[directory / 'candidate' / task['primary_file'], directory / 'implementer-handoff.json',
                             directory / 'architect-result.json', repository / task['primary_file']])
        assessment['roles'].append(tester)
        save(directory, 'independent_tester-execution', tester)
        require(tester['execution_status'] == 'completed', 'Independent Tester failed')
        design_bytes = (workspace / 'tests/test-design.json').read_bytes()
        harness = (workspace / 'tests/test_stage26_acceptance.py').read_bytes()
        remove(workspace, tester)
        contract = SimpleNamespace(TASK=task, strict_json=json.loads,
            validate_design=lambda b: validate_json(b, DESIGN_SCHEMA), acceptance_source=lambda _: harness.decode())
        freeze, _, design = freeze_design(directory, design_bytes, contract)
        assessment['tester_candidate_blind_before_freeze'] = True
        assessment['independent_design_cases'] = len(design['cases'])
        stage = 'baseline_control'
        baseline = run_control(runner, directory, files, harness, runtime, 'baseline-control', ['tests/test_stage26_acceptance.py'])
        assessment['baseline_control'] = baseline
        require(baseline['exit_code'] == 0 and baseline['tests'] >= 8 and not baseline['skipped'],
                'Frozen independent suite fails original behavior')
        stage = 'regression_controls'
        # Predeclared public behavior mutations; never replace or repair the candidate.
        mutations = {
            'wrong-outcome-control': '''\n_stage26_original_loader = load_steam_store_file
def load_steam_store_file(file_path: Path, snapshot_date: str) -> str:
    _stage26_original_loader(file_path, snapshot_date)
    return "incorrect_outcome"
''',
            'replay-counter-control': '''\n_stage26_original_mark = mark_steam_store_enrichment_result
def mark_steam_store_enrichment_result(appid: int, outcome: str, error_message: str | None = None,
    redirect_to: int | None = None, fetched_at: str | None = None, is_replay: bool = False) -> None:
    return _stage26_original_mark(appid, outcome, error_message, redirect_to, fetched_at, False)
'''}
        controls = {}
        for name, mutation in mutations.items():
            mutated = dict(files)
            mutated.update(candidate)
            mutated['src/load.py'] += mutation.encode()
            archive(directory, name + '-mutation.py.txt', mutation.encode())
            controls[name] = run_control(runner, directory, mutated, harness, runtime,
                                        name, ['tests/test_stage26_acceptance.py'])
            require(controls[name]['failed'] > 0 and not controls[name]['errors'],
                    'Independent tests failed to detect deliberate behavior mutation')
        assessment['regression_controls'] = controls
        require_frozen(directory, freeze)
        stage = 'acceptance'
        env = {'POSTGRES_HOST': runtime['socket'], 'POSTGRES_PORT': '55425', 'POSTGRES_USER': 'stage25',
               'POSTGRES_PASSWORD': 'disposable-local-only', 'POSTGRES_DB': 'unused',
               'REQUIRE_DB_TESTS': '1', 'PYTHONDONTWRITEBYTECODE': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'}
        acceptance_and_review(runner, directory, files, candidate, patch, canonical, freeze, design,
            runtime, assessment, owned, env, acceptance_module='test_stage26_acceptance',
            reviewer_focus='Assess genuine engineering value: responsibilities/coupling, removed duplication, '
            'testability/readability, new abstractions, preserved callers and concrete regressions. '
            'A pointless refactoring does not merit unqualified acceptance. Baseline independent tests passed; '
            'two predeclared behavior controls produced assertion failures without setup errors.')
    except Exception as error:
        assessment.update(failed_stage=assessment.get('_active_stage', stage),
            failure_category='required_workflow_evidence_failed', failure_type=type(error).__name__,
            failure_reason=str(error)[:1000])
    finally:
        failures = []
        for workspace in owned:
            if workspace.exists():
                try:
                    cleanup(workspace)
                except Exception as error:
                    failures.append(str(error))
        after = source_fingerprint(repository)
        save(directory, 'original-after', after)
        assessment['original_unchanged'] = original == after
        assessment['cleanup_passed'] = not failures and all(not p.exists() for p in owned)
        assessment['cleanup_failures'] = failures
        assessment['owned_workspaces'] = [str(p) for p in owned]
        assessment['accepted'] = assessment['accepted'] and original == after and assessment['cleanup_passed']
        assessment['outcome'] = 'PASS' if assessment['accepted'] else 'FAIL'
        assessment['elapsed_seconds'] = round(time.time() - assessment['started_at'], 3)
        save(directory, 'assessment', assessment)
        save(directory, 'controller-decision', {k: assessment[k] for k in
            ('accepted', 'outcome', 'original_unchanged', 'cleanup_passed', 'failure_category')})
    print(json.dumps({k: v for k, v in assessment.items() if k not in ('roles', 'review')}, indent=2), flush=True)
    return 0 if assessment['accepted'] else 1


def run_control(runner, directory, files, harness, runtime, name, selected):
    workspace = owned_workspace(dict(files, **{'tests/test_stage26_acceptance.py': harness, 'checks/.keep': b''}))
    try:
        service = RoleTestEnvironment(runner, runtime, directory, {name: ['pytest', *selected]},
                                      database='stage26_control', evidence_prefix=name)
        service.workspace = workspace
        result = service.execute(name)
        (directory / (name + '-1.json')).replace(directory / (name + '.json'))
        junit = directory / (name + '-1.xml')
        require(junit.exists(), 'Control did not produce JUnit')
        junit.replace(directory / (name + '.xml'))
        cases = list(ET.parse(directory / (name + '.xml')).iter('testcase'))
        return dict(result, tests=len(cases), failed=sum(t.find('failure') is not None for t in cases),
                    errors=sum(t.find('error') is not None for t in cases),
                    skipped=sum(t.find('skipped') is not None for t in cases))
    finally:
        cleanup(workspace)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'run'])
    parser.add_argument('--repository', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    return (prepare if args.mode == 'prepare' else run)(args)


if __name__ == '__main__':
    raise SystemExit(main())
