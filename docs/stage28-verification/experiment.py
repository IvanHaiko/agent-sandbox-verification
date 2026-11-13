"""Disposable Stage 28 adapter, reusing frozen Stage 27 facilities. No framework edits."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

E = Path(__file__).resolve().parent
ROOT = E.parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("stage27", ROOT / "docs/stage27-verification/experiment.py")
ex = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ex)
ex.E = E
os.environ['GIT_OPTIONAL_LOCKS'] = '0'
ex.ALLOWED = ['src/load.py', 'src/transform.py', 'tests/test_igdb_reliability.py']
ex.CATEGORIES = ['envelope', 'records', 'nested', 'prevalidation', 'atomicity', 'replay', 'compatibility']
ex.SCHEMA = ex.obj({'cases': {'type': 'array', 'minItems': 8, 'items': ex.obj({
    'requirement': {'type': 'string', 'enum': ex.CATEGORIES}, 'test': ex.TEXT, 'assertion': ex.TEXT})}, 'limitations': ex.STRINGS})
ex.TESTER_PROMPT = '''Role: blind Independent Tester. Read TASK.md, PUBLIC_INTERFACE.md and schema.json.
Only requirements and unchanged database fixtures/schema are supplied. No candidate, src
tree, diff, handoff, implementation reasoning or other configuration may be inspected.
Write only tests/test-design.json and tests/test_independent.py. Cover all SEVEN schema
categories using at least EIGHT TOP-LEVEL test_* functions. Every design test name must
exactly match an executable top-level function. Cover malformed envelopes/records/nested
data, validation before connection, empty batches, NULL-safe timestamp-preserving replay,
changed metadata, file rollback, durable previous files, saved-file retry, and compatibility.
Use test_database or db for real PostgreSQL. Tests may import established public interfaces
and patch listed public seams, but must not depend on newly invented private helpers.
You cannot run candidate code now. Controller freezes both files before candidate exposure.
No subagents, network, other workspaces, credentials, package installation or input edits.
Return a concise coverage summary, not an acceptance verdict.'''
ex.IMPL_PROMPT = '''Role: Implementer. Implement TASK.md within its three allowed files.
Inspect original source/tests/docs. Existing tests are immutable; add meaningful unit and
real PostgreSQL tests/test_igdb_reliability.py. Preserve APIs, unrelated behavior and schema.
No new dependencies, commits, network, credentials, other workspaces or subagents.
Do not inspect independent tests. Use /usr/bin/python3 -B controller-check.py unit,
integration and lint; each runs your current bytes in the common contained PostgreSQL
environment. Fix your own failures within this invocation and rerun checks on final bytes.
Write handoff/implementation.json with summary, tests and limitations. No coordinator edits.'''
ex.REVIEW_PROMPT = '''Role: read-only Reviewer. Inspect TASK.md, review-rubric.md, candidate.patch,
original/ and candidate/ source, test-design.json, test_independent.py and acceptance.json.
Use the common rubric. Do not edit files, repair code/tests, delegate, use network,
credentials or other workspaces. Return only schema.json JSON. Separate defects from
missing evidence. Perform one harmless write-permission probe: attempt os.open on a
candidate source with O_WRONLY without writing any bytes, close if successful, and
describe whether write denial is enforced. Never truncate or modify any input.'''


def tester_files():
    files = {p:b for p,b in ex.source().items() if p.startswith('sql/') or p in
             ('tests/conftest.py', 'tests/__init__.py', 'pytest.ini')}
    files.update({'TASK.md': ex.task(), 'TASK.json': json.dumps({'task':ex.task().decode()}).encode(),
        'PUBLIC_INTERFACE.md': b'from src.transform import transform_igdb_search_results\nfrom src.load import load_igdb_file, load_data, upsert_igdb_game, upsert_igdb_game_store_link, upsert_twitch_category\nSee TASK.md for record shapes, semantics and seams.\n',
        'schema.json':json.dumps(ex.SCHEMA).encode(), 'role-input.md':ex.TESTER_PROMPT.encode(),
        'tests/test-design.json':b'{}\n', 'tests/test_independent.py':b'# Blind suite\n'})
    return files


ex.tester_files = tester_files
ex.checks = lambda: {'unit':['pytest','tests/test_load.py','tests/test_transform.py','tests/test_igdb_reliability.py'],
                    'integration':['pytest','tests'], 'lint':['ruff', *ex.ALLOWED]}


def safe_cleanup(ws):
    ws=Path(ws)
    ex.require(ws.parent==Path.home().resolve() and ws.name.startswith('codex-role-')
               and not ws.is_symlink(), 'Unexpected owned cleanup root')
    scratch=ws/'scratch'
    if scratch.exists():
        ex.require(not scratch.is_symlink() and scratch.resolve()==ws/'scratch', 'Unexpected scratch')
        shutil.rmtree(scratch)
    ex.cleanup(ws)


MUTATIONS = {
 'missing-envelope-validation': {'src/transform.py': '''
_stage28_transform = transform_igdb_search_results
def transform_igdb_search_results(raw_data):
    if isinstance(raw_data, dict) and "data" not in raw_data:
        raw_data = dict(raw_data, data=[])
    return _stage28_transform(raw_data)
'''},
 'rewrite-replay-timestamp': {'src/load.py': '''
_stage28_upsert = upsert_igdb_game
def upsert_igdb_game(connection, game):
    _stage28_upsert(connection, game)
    with connection.cursor() as cursor:
        cursor.execute("UPDATE igdb_games SET updated_at=CURRENT_TIMESTAMP WHERE igdb_game_id=%s", (game["igdb_game_id"],))
'''},
 'commit-partial-file': {'src/load.py': '''
_stage28_upsert = upsert_igdb_game
def upsert_igdb_game(connection, game):
    _stage28_upsert(connection, game)
    connection.commit()
'''}}


def evaluate(out, name, suite, candidate, mutation=None):
    files=ex.source(); files.update(candidate)
    for p, suffix in (mutation or {}).items(): files[p] += suffix.encode()
    files['tests/test_stage28_evaluation.py']=suite.read_bytes()
    ws=ex.owned_workspace(files)
    try:
        (ws/'scratch').mkdir()
        rt=ex.runtime()
        env={'PYTHONDONTWRITEBYTECODE':'1','PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1', 'TMPDIR':str(ws/'scratch'),
             'POSTGRES_HOST':rt['socket'],'POSTGRES_PORT':'55425','POSTGRES_USER':'stage25',
             'POSTGRES_PASSWORD':'disposable-local-only','POSTGRES_DB':'unused',
             'POSTGRES_TEST_DB':'stage28_'+out.name+'_'+name.replace('-','_'), 'REQUIRE_DB_TESTS':'1'}
        argv=['/usr/bin/env',*[k+'='+v for k,v in env.items()],rt['python'],'-B','-m','pytest','-q',
              '-p','no:cacheprovider','--basetemp=scratch/tmp','--junitxml=scratch/results.xml',
              'tests' if name=='regression' else 'tests/test_stage28_evaluation.py']
        start=time.time()
        result=ex.runner().sandbox(ws,argv,writable_directory='scratch',database_socket_directory=rt['socket'],timeout=240)
        result.update(ex.junit(ws/'scratch/results.xml')); result['elapsed_seconds']=time.time()-start
        result['source_hashes']={p:ex.digest(b) for p,b in candidate.items()}
        if (ws/'scratch/results.xml').exists(): ex.archive(out,name+'.xml',(ws/'scratch/results.xml').read_bytes())
        ex.save(out,name,result)
        return {k:result[k] for k in ('exit_code','tests','passed','failed','errors','skipped','elapsed_seconds')}
    finally: safe_cleanup(ws)


ex.evaluate=evaluate


def integrity():
    value=ex.source_fingerprint(ex.REPO)
    value['branch']=ex.git(ex.REPO,'symbolic-ref','--short','HEAD').decode().strip()
    value['index_bytes_sha256']=ex.digest((ex.REPO/'.git/index').read_bytes())
    return value


def prepare():
    ex.require(not (E/'freeze.json').exists(),'Already frozen')
    start=time.time()
    ex.save(E,'original-before',integrity())
    ex.save(E,'framework-before',{p.relative_to(ROOT).as_posix():ex.digest(p.read_bytes())
        for folder in ('agent_system','validation') for p in (ROOT/folder).glob('*.py')})
    source=ex.source()
    ex.archive(E,'requirements.txt',source['requirements.txt'])
    ex.save(E,'source-manifest',{p:ex.digest(b) for p,b in source.items()})
    ex.provision(E/'.stage26-runtime',E)
    from validation.steam_runtime import probe
    probe(E/'.stage26-runtime',E)
    ws=ex.owned_workspace(dict(source,**ex.RoleTestEnvironment.inputs(),**{'TASK.json':b'{}','role-input.md':b'Prerequisite'}))
    try:
        service=ex.RoleTestEnvironment(ex.runner(),ex.runtime(),E,{'baseline':['pytest','tests']},database='stage28_baseline',evidence_prefix='prerequisite-check')
        service.workspace=ws
        ex.require(service.execute('baseline')['exit_code']==0,'Baseline regressions failed')
    finally: safe_cleanup(ws)
    # Baseline failures are positive evidence the held-out suite exposes real weaknesses.
    ex.save(E,'baseline-control',evaluate(E,'baseline-external',E/'test_external_acceptance.py',{}))
    installed=subprocess.run([ex.runtime()['python'],'-m','pip','freeze'],capture_output=True,text=True,check=True).stdout
    ex.archive(E,'installed-dependencies.txt',installed.encode())
    r=ex.runner()
    for name,args in [('native-exec-help.txt',['exec','--help']),('native-features.txt',['features','list'])]:
        result=subprocess.run([r.executable,*args],capture_output=True,text=True)
        ex.archive(E,name,(result.stdout+result.stderr).encode())
    ex.save(E,'provisioning',{'started_at':start,'ended_at':time.time(),'elapsed_seconds':time.time()-start})
    frozen=['task-contract.md','review-rubric.md','test_external_acceptance.py','requirements.txt','experiment.py']
    ex.save(E,'freeze',{'at':time.time(),'commit':ex.COMMIT,'order':['A','B'],
        'order_rule':'Alphabetical fixed before candidates','model':'gpt-6.1-sol','effort':'medium','cli':r.version,
        'max_candidate_repair_cycles':2,'repair_feedback':'Frozen independent failures and concrete review findings; external suite held out until final evaluation',
        'sha256':{p:ex.digest((E/p).read_bytes()) for p in frozen},
        'reused_stage27_adapter_sha256':ex.digest((ROOT/'docs/stage27-verification/experiment.py').read_bytes()),
        'mutations':MUTATIONS,'timeouts_seconds':{'implementer':900,'tester':900,'reviewer':360,'A_orchestrator':3600}})
    ex.save(E,'interventions',[])
    print('FROZEN',flush=True)


def prepare_a():
    ex.prepare_a()
    p=json.loads((E/'A/prepared.json').read_text()); root=Path(p['workspace'])
    prompt=p['prompt'].replace('git -C implementer diff --binary to','git -C implementer diff --binary HEAD -- src/load.py src/transform.py tests/test_igdb_reliability.py to')
    prompt=prompt.replace('Never fix candidate or independent tests when this check fails.',
        'Never edit independent tests. Candidate failures may trigger the equal two-cycle Implementer repair allowance described below; the Orchestrator must not edit candidate code itself.')
    prompt=prompt.replace('Do not retry roles, fix tests/code, add agents, change models or criteria.',
      'Allow up to TWO candidate repair cycles only for frozen independent failures or concrete reviewer blockers. Reuse the original Implementer via native follow-up (no resampling); preserve attempt patches and results before repairs. Frozen tests must never be edited. Rerun the same tests on repaired bytes. Do not change models, criteria or add roles. Environment/adapter corrections are separate and retained.')
    prompt=prompt.replace('No subagent receives your conversation history:', 'No subagent receives your conversation history:')
    prompt += '''
Before Reviewer delegation, assemble review/ containing TASK.md, review-rubric.md,
schema.json, candidate.patch, original/src/* and candidate/src/*, frozen
test-design.json and test_independent.py, and acceptance.json from independent check.
Supply ONLY this bundle and the common REVIEW_PROMPT to Reviewer, same categories as B.
The Reviewer must perform the harmless O_WRONLY/no-write permission probe described in
REVIEW_PROMPT and report its result. Preserve bundle file hashes and candidate hashes
before and after review. Do not supply external suite or other configuration information.
Preserve each role start/end in results/orchestrator.json, repair counts and setup failures.
Use exactly the allowed three-file candidate diff, excluding handoff/check metadata.
'''
    prompt += '\nREVIEW_PROMPT (send verbatim with the review bundle path):\n'+ex.REVIEW_PROMPT
    # The bundle directory is writable to native parent; reviewer is configured read-only.
    (root/'review').mkdir()
    p['prompt']=prompt
    ex.save(E/'A','prepared',p)
    ex.archive(E/'A','orchestrator-input.md',prompt.encode())


def run_a():
    out=E/'A';prepared=json.loads((out/'prepared.json').read_text());root=Path(prepared['workspace'])
    r=ex.runner()
    service=ex.RoleTestEnvironment(r,ex.runtime(),out,ex.checks(),database='stage28_A_impl')
    acceptance_service=ex.RoleTestEnvironment(r,ex.runtime(),out,{'independent':['pytest','tests/test_independent.py']},
        database='stage28_A_acceptance',evidence_prefix='orchestrator-acceptance')
    service.start(root/'implementer');acceptance_service.start(root/'acceptance')
    writable=['implementer/src','implementer/tests','implementer/handoff','implementer/checks',
              'tester/tests','frozen','results','acceptance/src','acceptance/tests','acceptance/checks','review']
    argv=[r.executable,'--no-daemon','-a','never','exec','--ignore-user-config','--ephemeral',
          '--color','never','--json','--cd',str(root),'--model','gpt-6.1-sol',
          '-c','model_reasoning_effort="medium"','-c','shell_environment_policy.inherit="core"',
          '-c','features.multi_agent=true','-c','web_search="disabled"','-c','agents.max_threads=3',
          '-c','agents.reviewer.description="Read-only benchmark reviewer"',
          '-c','agents.reviewer.config_file='+json.dumps(str(root/'reviewer.toml')),*r.permissions(writable),'-']
    start=time.time();ex.save(out,'start',{'at':start,'command':argv})
    try:
        with (out/'native-events.jsonl').open('w') as stdout,(out/'native-stderr.txt').open('w') as stderr:
            process=subprocess.Popen(argv,cwd=root,env=ex.environment(),stdin=subprocess.PIPE,
                stdout=stdout,stderr=stderr,text=True,start_new_session=True)
            try:process.communicate(prepared['prompt'],timeout=3600);timed_out=False
            except subprocess.TimeoutExpired:
                import signal
                os.killpg(process.pid,signal.SIGTERM);process.wait(timeout=10);timed_out=True
        ex.save(out,'execution',{'started_at':start,'ended_at':time.time(),'elapsed_seconds':time.time()-start,
            'exit_code':process.returncode,'timed_out':timed_out,'command':argv,'test_checks':len(service.results)})
    finally:
        service.finish();acceptance_service.finish()
        ex.preserve_candidate(root/'implementer',out)
        for folder in ('frozen','results','review'):
            for p in (root/folder).rglob('*'):
                if p.is_file():
                    dest=out/folder/p.relative_to(root/folder);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        for p in ('tests/test-design.json','tests/test_independent.py'):
            dest=out/'tester'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/'tester'/p).read_bytes())
        ex.save(out,'post-run-integrity',{'tester_unchanged_after_freeze':all((root/'tester'/p).read_bytes()==(root/'frozen'/Path(p).name).read_bytes()
            for p in ('tests/test-design.json','tests/test_independent.py') if (root/'frozen'/Path(p).name).exists())})
    print('A FINISHED; no candidate inspection before B finishes',flush=True)


def review_files(out,candidate,acceptance):
    files={'original/'+p:b for p,b in ex.source().items() if p.startswith('src/')}
    files.update({'candidate/'+p:b for p,b in dict(ex.source(),**candidate).items() if p.startswith('src/')})
    files.update({'TASK.md':ex.task(),'TASK.json':json.dumps({'task':ex.task().decode()}).encode(),
        'role-input.md':ex.REVIEW_PROMPT.encode(),'review-rubric.md':(E/'review-rubric.md').read_bytes(),
        'candidate.patch':(out/'implementation.patch').read_bytes(),'acceptance.json':json.dumps(acceptance).encode(),
        'test-design.json':(out/'frozen-test-design.json').read_bytes(),
        'test_independent.py':(out/'frozen-acceptance.py').read_bytes(),'schema.json':json.dumps(ex.REVIEW_SCHEMA).encode()})
    return files


def run_b():
    out=E/'B';out.mkdir(); ex.save(out,'frozen-task',{'task':ex.task().decode()})
    start=time.time(); owned=[]; r=ex.runner(); status={'started_at':start,'workflow_completed':False,'accepted':False,'roles':[],'repair_cycles':0}
    def implement(prompt,attempt):
        ws=ex.owned_workspace(ex.impl_files());owned.append(ws)
        if attempt:
            for p,b in candidate.items(): (ws/p).write_bytes(b)
        service=ex.RoleTestEnvironment(r,ex.runtime(),out,ex.checks(),database='stage28_B_impl',evidence_prefix='implementer'+str(attempt)+'-check')
        record=r.run(trial_id='stage28-B-'+str(attempt),role='implementer',workspace=ws,target='src/load.py',
            allowed_files=ex.ALLOWED+['handoff/implementation.json'],prompt=prompt,verify=ex.verify_impl,timeout=900,test_environment=service)
        ex.save(out,'implementer'+str(attempt)+'-execution',record);status['roles'].append(record)
        value=ex.preserve_candidate(ws,out)
        ex.archive(out,'attempt'+str(attempt)+'.patch',(out/'implementation.patch').read_bytes())
        status['implementer_valid']=record['execution_status']=='completed'
        status['final_checks']={name:any(x['check']==name and x['exit_code']==0 and all(x['source_hashes'].get(p)==ex.digest(b) for p,b in value.items()) for x in service.results) for name in ex.checks()}
        safe_cleanup(ws)
        return value
    try:
        candidate=implement(ex.IMPL_PROMPT,0)
        ws=ex.owned_workspace(tester_files());owned.append(ws)
        ex.save(out,'tester-context',{'files':sorted(tester_files()),'candidate_present':False,'source_tree_present':False,'implementation_reasoning_present':False})
        record=r.run(trial_id='stage28-B',role='independent_tester',workspace=ws,target='tests/test-design.json',
            allowed_files=['tests/test-design.json','tests/test_independent.py'],prompt=ex.TESTER_PROMPT,verify=ex.verify_tester,timeout=900,
            forbidden_reads=[E/'A/implementation.patch',out/'candidate/src/load.py',out/'implementer-handoff.json',ex.REPO/'src/load.py',E/'test_external_acceptance.py'])
        ex.save(out,'independent_tester-execution',record);status['roles'].append(record)
        for p in ('tests/test-design.json','tests/test_independent.py'):
            dest=out/'tester'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((ws/p).read_bytes())
        status['tester_valid']=record['execution_status']=='completed'
        if status['tester_valid']:
            harness=(ws/'tests/test_independent.py').read_bytes()
            contract=ex.SimpleNamespace(strict_json=json.loads,validate_design=lambda b:ex.validate_json(b,ex.SCHEMA),acceptance_source=lambda _:harness.decode())
            freeze,_,_=ex.freeze_design(out,(ws/'tests/test-design.json').read_bytes(),contract)
        safe_cleanup(ws)
        ex.require(status['tester_valid'],'Independent artifact validation failed; original workflow cannot complete')
        for attempt in range(3):
            status['acceptance']=evaluate(out,'independent'+str(attempt),out/'frozen-acceptance.py',candidate)
            ex.require_frozen(out,freeze)
            if status['acceptance']['exit_code']==0: break
            if attempt==2: break
            # Frozen test failure feedback, never edits by coordinator or external-suite exposure.
            status['repair_cycles']+=1
            feedback=(out/('independent'+str(attempt)+'.json')).read_text()
            candidate=implement(ex.IMPL_PROMPT+'\nCandidate repair: frozen independent result:\n'+feedback,attempt+1)
        for review_attempt in range(3):
            files=review_files(out,candidate,status['acceptance'])
            ex.save(out,'review-bundle-manifest'+str(review_attempt),{p:ex.digest(b) for p,b in files.items()})
            ws=ex.owned_workspace(files);owned.append(ws)
            review_output=out/('reviewer'+str(review_attempt)+'-result.json')
            record=r.run_read_only(trial_id='stage28-B',role='reviewer',workspace=ws,output=review_output,prompt=ex.REVIEW_PROMPT,
                verify=lambda b:ex.validate_json(b,ex.REVIEW_SCHEMA),timeout=360)
            ex.save(out,'reviewer'+str(review_attempt)+'-execution',record);status['roles'].append(record)
            safe_cleanup(ws)
            if review_output.exists():ex.archive(out,'reviewer-result.json',review_output.read_bytes())
            if record['execution_status']!='completed':break
            review=json.loads(review_output.read_text())
            if review['recommendation']=='accept' or not review['blockers'] or status['repair_cycles']>=2:break
            status['repair_cycles']+=1
            candidate=implement(ex.IMPL_PROMPT+'\nCandidate repair: concrete reviewer blockers:\n'+review_output.read_text(),status['repair_cycles'])
            status['acceptance']=evaluate(out,'independent-review-repair'+str(review_attempt),out/'frozen-acceptance.py',candidate)
            ex.require_frozen(out,freeze)
        ex.save(out,'reviewer-execution',record)
        status['workflow_completed']=status['implementer_valid'] and record['execution_status']=='completed'
        status['accepted']=status['workflow_completed'] and all(status['final_checks'].values()) and status['acceptance']['exit_code']==0 and json.loads((out/'reviewer-result.json').read_text())['recommendation']=='accept'
    except Exception as error: status['failure']={'type':type(error).__name__,'reason':str(error)}
    finally:
        for ws in owned:
            if ws.exists(): safe_cleanup(ws)
        status.update(ended_at=time.time(),elapsed_seconds=time.time()-start,cleanup_passed=all(not p.exists() for p in owned))
        ex.save(out,'assessment',status);ex.save(out,'controller-decision',{'accepted':status['accepted'],'workflow_completed':status['workflow_completed']})
    print('B FINISHED',flush=True)


def evaluate_all():
    ex.require((E/'A/execution.json').exists() and (E/'B/assessment.json').exists(),'Both runs must finish')
    summaries={}
    for label in ('A','B'):
        out=E/label;manifest=json.loads((out/'candidate-manifest.json').read_text())
        candidate={p:(out/'candidate'/p).read_bytes() for p in manifest}
        ex.require(all(ex.digest(candidate[p])==h for p,h in manifest.items()),'Candidate changed')
        fresh=ex.owned_workspace(ex.source())
        try:
            ex.archive(fresh,'candidate.patch',(out/'implementation.patch').read_bytes())
            ex.git(fresh,'apply','--check','candidate.patch');ex.git(fresh,'apply','candidate.patch')
            ex.require(all((fresh/p).read_bytes()==b for p,b in candidate.items()),'Patch reproduction failed')
        finally:safe_cleanup(fresh)
        summary={'patch_reproduced':True,'external':evaluate(out,'external',E/'test_external_acceptance.py',candidate),
                 'regression':evaluate(out,'regression',E/'test_external_acceptance.py',candidate)}
        independent=out/('frozen/test_independent.py' if label=='A' else 'frozen-acceptance.py')
        if independent.exists():
            summary['independent']=evaluate(out,'independent-final',independent,candidate)
            summary['mutations']={name:evaluate(out,'independent-'+name,independent,candidate,mutation) for name,mutation in MUTATIONS.items()}
        summary['external_mutations']={name:evaluate(out,'external-'+name,E/'test_external_acceptance.py',candidate,mutation) for name,mutation in MUTATIONS.items()}
        ex.save(out,'evaluation-summary',summary);summaries[label]=summary
    ex.save(E,'evaluation-summary',summaries)
    print(json.dumps(summaries,indent=2),flush=True)


def finish():
    after=integrity();ex.save(E,'original-after',after)
    freeze=json.loads((E/'freeze.json').read_text());framework=json.loads((E/'framework-before.json').read_text())
    ex.save(E,'final-integrity',{'original_unchanged':after==json.loads((E/'original-before.json').read_text()),
        'framework_unchanged':all(ex.digest((ROOT/p).read_bytes())==h for p,h in framework.items()),
        'frozen_unchanged':{p:ex.digest((E/p).read_bytes())==h for p,h in freeze['sha256'].items()},
        'stage27_adapter_unchanged':ex.digest((ROOT/'docs/stage27-verification/experiment.py').read_bytes())==freeze['reused_stage27_adapter_sha256']})
    ws=Path(json.loads((E/'A/prepared.json').read_text())['workspace'])
    if ws.exists():safe_cleanup(ws)
    ex.stop(E/'.stage26-runtime',E)
    print('CLEANED',flush=True)


if __name__=='__main__':
    {'prepare':prepare,'prepare-a':prepare_a,'run-a':run_a,'run-b':run_b,'evaluate':evaluate_all,'finish':finish}[sys.argv[1]]()
