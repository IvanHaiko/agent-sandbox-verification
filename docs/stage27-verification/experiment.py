"""One-off Stage 27 experiment notes/adapter. A uses native CLI delegation, not a runner."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent_system.artifacts import archive, cleanup, digest, freeze_design, owned_workspace, require, require_frozen, save, snapshot
from agent_system.native_codex_linux import NativeLinuxCodexRunner, environment
from agent_system.roles import obj, TEXT, STRINGS, REVIEW_SCHEMA
from agent_system.test_environment import RoleTestEnvironment
from validation.steam_workflow import fixed_source, git, source_fingerprint, validate_json
from validation.steam_runtime import provision, stop

E = Path(__file__).resolve().parent
REPO = Path('/mnt/c/Users/4ivan/steam-etl')
COMMIT = '0653617666399590c853c39f08e8cf97c9eca45c'
ALLOWED = ['src/migrations.py', 'src/sql_statements.py', 'tests/test_migration_sql.py']
CATEGORIES = ['boundaries', 'quotes', 'dollars', 'comments', 'errors', 'persistence', 'compatibility']
SCHEMA = obj({'cases': {'type': 'array', 'minItems': 8, 'items': obj({
    'requirement': {'type': 'string', 'enum': CATEGORIES}, 'test': TEXT, 'assertion': TEXT})}, 'limitations': STRINGS})
TESTER_PROMPT = '''Role: blind Independent Tester. Read TASK.md, PUBLIC_INTERFACE.md and schema.json.
Only original requirements and unchanged database fixtures/schema are provided. No candidate,
src tree, implementation reasoning or other configuration may be inspected. Write only
tests/test-design.json and tests/test_independent.py. Independently cover all seven schema
categories with at least EIGHT TOP-LEVEL test_* functions; every design test name must exactly
match a top-level executable function. Cover real PostgreSQL rollback, prior-file commits,
replay, lexical edge cases and separate statement execution. Use test_database fixture for
database tests and a unique schema with patched src.migrations.get_db_connection to isolate
the migration ledger; do not mix your own migrations with the fixture's public ledger.
Import the new interface inside tests/fixtures so test collection on the old source is valid.
Tests should reject old behavior: this task adds functionality. No private helper assumptions.
You cannot run candidate code now. Controller freezes both files before candidate exposure.
Do not use subagents, network, other workspaces, credentials, install packages or edit inputs.
Return a summary of coverage, not an acceptance verdict.'''
IMPL_PROMPT = '''Role: Implementer. Implement TASK.md within its exact allowed files.
Read original project source/tests/docs. Preserve original tests and APIs, add meaningful
tests/test_migration_sql.py. No extra dependencies, migrations, unrelated code, commits,
network, credentials, other workspaces or subagents. Do not inspect independent tests.
Use /usr/bin/python3 -B controller-check.py unit, then integration, then lint; these execute
your current files in the common disposable PostgreSQL test environment. Fix your own
failures within this single invocation, rerun final checks after your final changes.
Write handoff/implementation.json with summary, tests and limitations. No coordinator repairs.'''
REVIEW_PROMPT = '''Role: read-only Reviewer. Inspect TASK.md, review-rubric.md, candidate.patch,
original source and candidate source, own independent test design and acceptance.json.
Assess concrete correctness and quality using the common rubric. Do not edit any file,
run implementation repairs, delegate, use network, credentials or other workspaces.
Return schema.json structured output. Distinguish unverified requirements from defects.'''

def source():
    return fixed_source(REPO, COMMIT)

def task():
    return (E / 'task-contract.md').read_bytes()

def runtime():
    return json.loads((E / 'runtime.json').read_text())

def runner():
    return NativeLinuxCodexRunner(read_paths=(Path(runtime()['root']) / 'python',))

def junit(path):
    if not path.exists():
        return {'tests': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0}
    cases = list(ET.fromstring(path.read_bytes()).iter('testcase'))
    counts = {k: sum(c.find(tag) is not None for c in cases) for k, tag in
              [('failed', 'failure'), ('errors', 'error'), ('skipped', 'skipped')]}
    return dict(tests=len(cases), passed=len(cases)-sum(counts.values()), **counts)

def tester_files():
    files = {p: b for p, b in source().items() if p.startswith('sql/') or
             p in ('tests/conftest.py', 'tests/__init__.py', 'pytest.ini')}
    files.update({'TASK.md': task(), 'TASK.json': json.dumps({'task': task().decode()}).encode(),
        'PUBLIC_INTERFACE.md': b'from src.sql_statements import split_sql_statements\nfrom src.migrations import run_migrations\nPatch seam: src.migrations.get_db_connection\n',
        'schema.json': json.dumps(SCHEMA).encode(), 'role-input.md': TESTER_PROMPT.encode(),
        'tests/test-design.json': b'{}\n', 'tests/test_independent.py': b'# Blind independent suite\n'})
    return files

def impl_files():
    files = source()
    files.update(RoleTestEnvironment.inputs())
    files.update({'TASK.md': task(), 'TASK.json': json.dumps({'task': task().decode()}).encode(),
        'role-input.md': IMPL_PROMPT.encode(), 'handoff/implementation.json': b'{}\n'})
    return files

def checks():
    return {'unit': ['pytest', 'tests/test_migrations.py', 'tests/test_migration_sql.py'],
            'integration': ['pytest', 'tests'], 'lint': ['ruff', *ALLOWED]}

def verify_tester(files):
    value = json.loads(files['tests/test-design.json'])
    validate_json(json.dumps(value), SCHEMA)
    require({c['requirement'] for c in value['cases']} == set(CATEGORIES), 'Missing test category')
    tree = ast.parse(files['tests/test_independent.py'].decode())
    names = {n.name for n in tree.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
    require(len(names) >= 8 and {c['test'] for c in value['cases']} <= names, 'Design/harness mismatch')
    return {'valid': True, 'top_level_tests': len(names)}

def verify_impl(files):
    require(all(p in files for p in ALLOWED), 'Missing implementation/test file')
    for p in ALLOWED:
        ast.parse(files[p].decode())
    value = json.loads(files['handoff/implementation.json'])
    require('summary' in value and 'tests' in value, 'Invalid handoff')
    return {'valid': True}

def preserve_candidate(workspace, out):
    names = git(workspace, 'status', '--porcelain', '-uall').decode()
    candidate = {p: (workspace / p).read_bytes() for p in ALLOWED if (workspace / p).exists()}
    for p, b in candidate.items():
        path = out / 'candidate' / p
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b)
    for p in candidate:
        if p not in source():
            git(workspace, 'add', '--intent-to-add', '--', p)
    patch = git(workspace, 'diff', '--binary', 'HEAD', '--', *candidate)
    archive(out, 'implementation.patch', patch)
    save(out, 'candidate-manifest', {p: digest(b) for p, b in candidate.items()})
    save(out, 'candidate-status', {'status': names})
    if (workspace / 'handoff/implementation.json').exists():
        archive(out, 'implementer-handoff.json', (workspace / 'handoff/implementation.json').read_bytes())
    return candidate

def prepare():
    require(not (E / 'freeze.json').exists(), 'Already frozen')
    start = time.time()
    save(E, 'original-before', source_fingerprint(REPO))
    files = source()
    archive(E, 'requirements.txt', files['requirements.txt'])
    save(E, 'source-manifest', {p: digest(b) for p, b in files.items()})
    save(E, 'framework-before', {p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
        for folder in ('agent_system', 'validation') for p in (ROOT / folder).glob('*.py')})
    provision(E / '.stage26-runtime', E)
    from validation.steam_runtime import probe
    probe(E / '.stage26-runtime', E)
    rt = runtime()
    ws = owned_workspace(dict(files, **RoleTestEnvironment.inputs(), **{'TASK.json': b'{}', 'role-input.md': b'Prerequisite'}))
    try:
        service = RoleTestEnvironment(runner(), rt, E, {'baseline': ['pytest', 'tests']},
            database='stage27_baseline', evidence_prefix='prerequisite-check')
        service.workspace = ws
        result = service.execute('baseline')
        require(result['exit_code'] == 0, 'Baseline regression prerequisite failed')
    finally:
        cleanup(ws)
    save(E, 'provisioning', {'started_at': start, 'ended_at': time.time(), 'elapsed_seconds': time.time()-start})
    frozen_names = ['task-contract.md', 'review-rubric.md', 'test_external_acceptance.py', 'requirements.txt', 'experiment.py']
    save(E, 'freeze', {'at': time.time(), 'commit': COMMIT, 'order': ['A', 'B'],
        'order_rule': 'Predeclared alphabetic labels, no expected-success selection',
        'model': 'gpt-6.1-sol', 'effort': 'medium', 'cli': runner().version,
        'sha256': {p: digest((E / p).read_bytes()) for p in frozen_names},
        'mutations': ['naive semicolon splitter', 'drop final split statement'],
        'intervention_policy': 'No role retries or coordinator repairs; environment failures retained',
        'timeouts_seconds': {'implementer': 900, 'tester': 900, 'reviewer': 360, 'A_orchestrator': 2400}})
    save(E, 'interventions', [])
    print('FROZEN', flush=True)

def prepare_a():
    out = E / 'A'; out.mkdir()
    root = owned_workspace({'TASK.md': task(), 'review-rubric.md': (E/'review-rubric.md').read_bytes(),
        'results/.keep': b'', 'frozen/.keep': b'', 'role-input.md': b'Native A orchestrator', 'TASK.json': b'{}'})
    for name, files in [('implementer', impl_files()), ('tester', tester_files()),
                        ('acceptance', dict(source(), **RoleTestEnvironment.inputs()))]:
        sub = root / name
        for p, b in files.items():
            path = sub / p; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b)
        git(sub, 'init', '--initial-branch=main')
        git(sub, 'add', '.')
        git(sub, '-c', 'user.name=Benchmark', '-c', 'user.email=benchmark@example.invalid', 'commit', '-m', 'Pinned source')
        if name == 'implementer':
            for p in ALLOWED:
                if p not in source():
                    (sub / p).write_bytes(b'')
                    git(sub, 'add', '--intent-to-add', '--', p)
    # Native agent configuration only. No custom orchestration code in A.
    reviewer_config = 'model = "gpt-6.1-sol"\nmodel_reasoning_effort = "medium"\nsandbox_mode = "read-only"\ndeveloper_instructions = "Read-only reviewer. Never edit files or delegate. Use the common rubric."\n'
    (root / 'reviewer.toml').write_text(reviewer_config)
    prompt = f'''You are Configuration A Orchestrator in a controlled engineering benchmark.
Use native multi-agent tools and exactly three subagents: Independent Tester, Implementer,
Reviewer. All must use gpt-6.1-sol with medium reasoning; no substitutions or extra agents.
Do not implement or repair candidate code yourself. Do not inspect outside this root.
No subagent receives your conversation history: use fresh/empty context (fork_context=false
or equivalent if offered). Each prompt must contain only the role's requirements.
All inputs are prepared. Read TASK.md for contract. Only the Implementer gets source docs.
1. First spawn blind Independent Tester working only in {root}/tester, with prompt:
{TESTER_PROMPT}
Wait for completion (900s limit). Do not expose implementer source to Tester.
2. Preserve both tester files byte-for-byte into frozen/test-design.json and frozen/test_independent.py.
Write results/test-freeze.json with sha256 hashes and time.time(), candidate_visible=false.
No candidate implementation has begun. Do not edit frozen tests even if they later fail.
3. Spawn Implementer working only in {root}/implementer with prompt:
{IMPL_PROMPT}
Wait for completion (900s limit). Do not give tester code or reasoning to Implementer.
4. Preserve implementation diff using git -C implementer diff --binary to
results/implementation.patch. The two new files already have intent-to-add entries;
Git metadata is read-only, so do not run git add or commit.
5. Apply the exact candidate patch to the separate pinned acceptance copy, and copy frozen
test_independent.py unchanged to acceptance/tests/test_independent.py. Execute
cd acceptance && /usr/bin/python3 -B controller-check.py independent and preserve its result.
Never fix candidate or independent tests when this check fails.
6. Spawn Reviewer using native reviewer agent type if available (otherwise explorer configured
read-only). Give only task, common rubric, candidate diff and relevant original/candidate code.
Include the frozen test design and independent check results, distinguishing test errors.
Reviewer cannot edit files. Prompt: assess code quality/regressions, return JSON with
recommendation, blockers, findings, rationale using {json.dumps(REVIEW_SCHEMA)}.
Preserve its returned JSON as results/reviewer-result.json yourself; Reviewer must not write it.
7. Write results/orchestrator.json with role ids, times, failures, freeze details, completion.
Do not retry roles, fix tests/code, add agents, change models or criteria. If a role fails,
preserve outputs and record failure. Native failure is a benchmark outcome.
No external acceptance suite is available. Evaluation happens separately after both runs.
'''
    archive(out, 'orchestrator-input.md', prompt.encode())
    save(out, 'prepared', {'workspace': str(root), 'prompt': prompt, 'tester_initial_files': sorted(tester_files()),
                          'implementer_initial_files': sorted(impl_files())})
    print(root, flush=True)

def run_a():
    out = E / 'A'; prepared = json.loads((out/'prepared.json').read_text()); root = Path(prepared['workspace'])
    r = runner()
    service = RoleTestEnvironment(r, runtime(), out, checks(), database='stage27_A_impl')
    service.start(root / 'implementer')
    acceptance_service = RoleTestEnvironment(r, runtime(), out,
        {'independent': ['pytest', 'tests/test_independent.py']}, database='stage27_A_acceptance',
        evidence_prefix='orchestrator-acceptance')
    acceptance_service.start(root / 'acceptance')
    writable = ['implementer/src', 'implementer/tests', 'implementer/handoff', 'implementer/checks',
                'tester/tests', 'frozen', 'results', 'acceptance/src', 'acceptance/tests', 'acceptance/checks']
    argv = [r.executable, '--no-daemon', '-a', 'never', 'exec', '--ignore-user-config', '--ephemeral',
        '--color', 'never', '--json', '--cd', str(root), '--model', 'gpt-6.1-sol',
        '-c', 'model_reasoning_effort="medium"', '-c', 'shell_environment_policy.inherit="core"',
        '-c', 'features.multi_agent=true', '-c', 'web_search="disabled"',
        '-c', 'agents.max_threads=3', '-c', 'agents.reviewer.description="Read-only benchmark reviewer"',
        '-c', 'agents.reviewer.config_file=' + json.dumps(str(root/'reviewer.toml')),
        *r.permissions(writable), '-']
    start = time.time(); save(out, 'start', {'at': start, 'command': argv})
    try:
        with (out/'native-events.jsonl').open('w') as stdout, (out/'native-stderr.txt').open('w') as stderr:
            process = subprocess.Popen(argv, cwd=root, env=environment(), stdin=subprocess.PIPE,
                stdout=stdout, stderr=stderr, text=True, start_new_session=True)
            try:
                process.communicate(prepared['prompt'], timeout=2400)
                timed_out = False
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid, signal.SIGTERM); process.wait(timeout=10); timed_out = True
        save(out, 'execution', {'started_at': start, 'ended_at': time.time(),
            'elapsed_seconds': time.time()-start, 'exit_code': process.returncode, 'timed_out': timed_out,
            'command': argv, 'test_checks': len(service.results)})
    finally:
        service.finish()
        acceptance_service.finish()
        preserve_candidate(root/'implementer', out)
        for folder in ('frozen', 'results'):
            for p in (root/folder).rglob('*'):
                if p.is_file():
                    dest = out/folder/p.relative_to(root/folder); dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(p.read_bytes())
        for p in ('tests/test-design.json', 'tests/test_independent.py'):
            dest = out/'tester'/p; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((root/'tester'/p).read_bytes())
        save(out, 'post-run-integrity', {'tester_unchanged_after_freeze': all(
            (root/'tester'/p).read_bytes() == (root/'frozen'/Path(p).name).read_bytes()
            for p in ('tests/test-design.json', 'tests/test_independent.py') if (root/'frozen'/Path(p).name).exists())})
    print('A FINISHED; not inspecting candidate before B finishes', flush=True)

def run_b():
    out = E / 'B'; out.mkdir()
    save(out, 'frozen-task', {'task': task().decode()})
    r = runner(); rt = runtime(); start = time.time(); owned = []
    status = {'started_at': start, 'workflow_completed': False, 'accepted': False, 'roles': []}
    try:
        ws = owned_workspace(impl_files()); owned.append(ws)
        service = RoleTestEnvironment(r, rt, out, checks(), database='stage27_B_impl')
        record = r.run(trial_id='stage27-B', role='implementer', workspace=ws,
            target='src/migrations.py', allowed_files=ALLOWED+['handoff/implementation.json'],
            prompt=IMPL_PROMPT, verify=verify_impl, timeout=900, test_environment=service)
        save(out, 'implementer-execution', record); status['roles'].append(record)
        candidate = preserve_candidate(ws, out)
        status['implementer_valid'] = record['execution_status'] == 'completed'
        status['final_checks'] = {name: any(x['check']==name and x['exit_code']==0 and
            all(x['source_hashes'].get(p)==digest(b) for p,b in candidate.items()) for x in service.results)
            for name in checks()}
        cleanup(ws)
        ws = owned_workspace(tester_files()); owned.append(ws)
        save(out, 'tester-context', {'files': sorted(tester_files()), 'candidate_present': False,
            'source_tree_present': False, 'implementation_reasoning_present': False})
        record = NativeLinuxCodexRunner().run(trial_id='stage27-B', role='independent_tester',
            workspace=ws, target='tests/test-design.json', allowed_files=['tests/test-design.json','tests/test_independent.py'],
            prompt=TESTER_PROMPT, verify=verify_tester, timeout=900,
            forbidden_reads=[E/'A/implementation.patch', out/'candidate/src/migrations.py', out/'implementer-handoff.json', REPO/'src/migrations.py'])
        save(out, 'independent_tester-execution', record); status['roles'].append(record)
        # Stage 26's existing collection-before-cleanup correction: preserve rejected bytes too.
        for p in ('tests/test-design.json', 'tests/test_independent.py'):
            dest=out/'tester'/p; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes((ws/p).read_bytes())
        status['tester_valid'] = record['execution_status'] == 'completed'
        if status['tester_valid']:
            harness=(ws/'tests/test_independent.py').read_bytes()
            contract=SimpleNamespace(strict_json=json.loads, validate_design=lambda b: validate_json(b, SCHEMA),
                                     acceptance_source=lambda _: harness.decode())
            freeze, _, _ = freeze_design(out, (ws/'tests/test-design.json').read_bytes(), contract)
        cleanup(ws)
        if status['tester_valid']:
            status['acceptance'] = evaluate(out, 'independent', out/'frozen-acceptance.py', candidate)
            require_frozen(out, freeze)
        else:
            status['acceptance'] = {'unavailable': 'Independent artifact validation failed'}
        save(out, 'acceptance', status['acceptance'])
        reviewfiles={ 'original/'+p:b for p,b in source().items() if p.startswith('src/') }
        reviewfiles.update({'candidate/'+p:b for p,b in dict(source(), **candidate).items() if p.startswith('src/')})
        reviewfiles.update({'TASK.md': task(), 'TASK.json': json.dumps({'task':task().decode()}).encode(),
            'role-input.md':REVIEW_PROMPT.encode(), 'review-rubric.md':(E/'review-rubric.md').read_bytes(),
            'candidate.patch':(out/'implementation.patch').read_bytes(), 'acceptance.json':json.dumps(status['acceptance']).encode(),
            'schema.json':json.dumps(REVIEW_SCHEMA).encode()})
        ws=owned_workspace(reviewfiles); owned.append(ws)
        record=r.run_read_only(trial_id='stage27-B', role='reviewer', workspace=ws,
            output=out/'reviewer-result.json', prompt=REVIEW_PROMPT,
            verify=lambda b:validate_json(b, REVIEW_SCHEMA), timeout=360)
        save(out,'reviewer-execution',record);status['roles'].append(record)
        status['workflow_completed']=status['implementer_valid'] and status['tester_valid'] and record['execution_status']=='completed'
        status['accepted']=status['workflow_completed'] and all(status['final_checks'].values()) and status['acceptance'].get('exit_code')==0 and json.loads((out/'reviewer-result.json').read_text())['recommendation']=='accept'
    except Exception as error:
        status['failure']={'type':type(error).__name__,'reason':str(error)}
    finally:
        for ws in owned:
            if ws.exists(): cleanup(ws)
        status.update(ended_at=time.time(), elapsed_seconds=time.time()-start, cleanup_passed=all(not p.exists() for p in owned))
        save(out,'assessment',status)
        save(out,'controller-decision',{'accepted':status['accepted'],'workflow_completed':status['workflow_completed']})
    print('B FINISHED',flush=True)

def evaluate(out, name, suite, candidate, mutation=None):
    files=source();files.update(candidate)
    if mutation:
        files['src/sql_statements.py'] += mutation.encode()
    files['tests/test_stage27_evaluation.py']=suite.read_bytes()
    ws=owned_workspace(files)
    try:
        (ws/'scratch').mkdir()
        rt=runtime()
        env={'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','POSTGRES_HOST':rt['socket'],
            'POSTGRES_PORT':'55425','POSTGRES_USER':'stage25','POSTGRES_PASSWORD':'disposable-local-only',
            'POSTGRES_DB':'postgres','POSTGRES_TEST_DB':'stage27_'+out.name+'_'+name.replace('-','_'),
            'REQUIRE_DB_TESTS':'1','TMPDIR':str(ws/'scratch')}
        argv=['/usr/bin/env',*[k+'='+v for k,v in env.items()],rt['python'],'-B','-m','pytest','-q',
              '-p','no:cacheprovider','--basetemp=scratch/tmp','--junitxml=scratch/results.xml',
              'tests' if name=='regression' else 'tests/test_stage27_evaluation.py']
        started=time.time()
        result=runner().sandbox(ws,argv,writable_directory='scratch',database_socket_directory=rt['socket'],timeout=180)
        result.update(junit(ws/'scratch/results.xml'));result['elapsed_seconds']=time.time()-started
        if (ws/'scratch/results.xml').exists():archive(out,name+'.xml',(ws/'scratch/results.xml').read_bytes())
        save(out,name,result)
        return {k:result[k] for k in ('exit_code','tests','passed','failed','errors','skipped','elapsed_seconds')}
    finally:
        cleanup(ws)

def evaluate_all():
    require((E/'A/execution.json').exists() and (E/'B/assessment.json').exists(),'Both executions must finish')
    mutations={
        'naive': '\ndef split_sql_statements(sql: str) -> list[str]:\n    return [p.strip() for p in sql.split(";") if p.strip()]\n',
        'drop-final':'\n_stage27_split_original = split_sql_statements\ndef split_sql_statements(sql: str) -> list[str]:\n    return _stage27_split_original(sql)[:-1]\n'}
    summaries={}
    for label in ('A','B'):
        out=E/label
        manifest=json.loads((out/'candidate-manifest.json').read_text())
        candidate={p:(out/'candidate'/p).read_bytes() for p in manifest}
        require(all(digest(candidate[p])==h for p,h in manifest.items()),'Candidate bytes changed')
        fresh=owned_workspace(source())
        try:
            archive(fresh,'candidate.patch',(out/'implementation.patch').read_bytes())
            git(fresh,'apply','--check','candidate.patch');git(fresh,'apply','candidate.patch')
            require(all((fresh/p).read_bytes()==b for p,b in candidate.items()),'Patch reproduction failed')
        finally: cleanup(fresh)
        summary={'patch_reproduced':True}
        summary['external']=evaluate(out,'external',E/'test_external_acceptance.py',candidate)
        summary['regression']=evaluate(out,'regression',E/'test_external_acceptance.py',candidate)
        independent=(out/'frozen/test_independent.py') if label=='A' else (out/'frozen-acceptance.py')
        if independent.exists():
            summary['independent']=evaluate(out,'independent-evaluation',independent,candidate)
            summary['mutations']={name:evaluate(out,'independent-'+name,independent,candidate,mutation)
                                  for name,mutation in mutations.items()}
        else:summary['independent']={'unavailable':True}
        summary['external_mutations']={name:evaluate(out,'external-'+name,E/'test_external_acceptance.py',candidate,mutation)
                                       for name,mutation in mutations.items()}
        save(out,'evaluation-summary',summary);summaries[label]=summary
    save(E,'evaluation-summary',summaries)
    print(json.dumps(summaries,indent=2),flush=True)

def finish():
    before=json.loads((E/'original-before.json').read_text());after=source_fingerprint(REPO)
    save(E,'original-after',after)
    frozen=json.loads((E/'freeze.json').read_text())
    framework=json.loads((E/'framework-before.json').read_text())
    save(E,'final-integrity',{'original_unchanged':before==after,
        'frozen_artifacts_unchanged':{p:digest((E/p).read_bytes())==h for p,h in frozen['sha256'].items()},
        'framework_unchanged':all(digest((ROOT/p).read_bytes())==h for p,h in framework.items())})
    prepared=json.loads((E/'A/prepared.json').read_text());ws=Path(prepared['workspace'])
    if ws.exists():cleanup(ws)
    stop(E/'.stage26-runtime',E)
    print('CLEANED',flush=True)

if __name__=='__main__':
    {'prepare':prepare,'prepare-a':prepare_a,'run-a':run_a,'run-b':run_b,
     'evaluate':evaluate_all,'finish':finish}[sys.argv[1]]()
