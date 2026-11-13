"""One task-specific live workflow. Stage19 transport is imported unchanged."""
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_system.agent_transport import InvocationBinding, strict_json
from agent_system.approvals import ApprovalStore
from agent_system.chatgpt_oauth import CredentialStore
from agent_system.codex_tool_session import CodexToolSession
from agent_system.config import Configuration
from agent_system.errors import AgentSystemError
from agent_system.git import git
from agent_system.isolation import IsolatedCheckout
from agent_system.model_tool_boundary import (ExecutionPolicy, IsolatedExecutionBridge,
    ResponsesGate, LocalModelRelay, PlanUpstream, SecretFilter, UPSTREAM)
import agent_system.model_tool_boundary as boundary
from agent_system.runners.tool_docker import ToolDockerRunner
from agent_system.runners.docker_isolated import CLEANUP, regular_tree, file_map
from agent_system.storage import atomic_json

OUT = ROOT / 'docs/stage20-evidence'
OWNED = ROOT / '.test-tmp/stage20-workflow'
TASK_ID = 'STAGE20-SLUGIFY'
ROUTES = {'orchestrator': ('gpt-6-astra', 'medium'),
          'implementer': ('gpt-5.6-sol', 'high'),
          'test_engineer': ('gpt-5.6-sol', 'high'), 'reviewer': ('gpt-6-astra', 'medium')}
CRITERIA = ['Lowercase ASCII letters; retain ASCII letters and digits.',
    'Trim whitespace and replace every whitespace run with one hyphen (including tabs/newlines).',
    'Remove ASCII punctuation except hyphen, including underscore; removal does not insert a separator.',
    'Collapse repeated hyphens and strip edge hyphens.', 'Empty or whitespace-only strings return the empty string.']
TASK = {'task_id': TASK_ID, 'contract_version': 1, 'public_interface': 'def slugify(value: str) -> str',
    'file': 'src/slugify.py', 'acceptance_criteria': CRITERIA,
    'examples': [['Hello World', 'hello-world'], ['  Hello   World ', 'hello-world'],
        ['Hello, World!', 'hello-world'], ['a---b', 'a-b'], ['---Hello---', 'hello'], ['', '']],
    'constraints': ['Pure Python, standard library only, no external dependencies or I/O.',
        'ASCII string inputs are in scope; Unicode and non-string behavior are unspecified.',
        'Do not add features or mutate any file other than src/slugify.py.']}

def require(ok, message):
    if not ok: raise AgentSystemError(message)

def load(path): return strict_json(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value): atomic_json(OUT / (name + '.json'), value)

def remove_owned(path, parent):
    path, parent = path.resolve(), parent.resolve()
    require(path != parent and path.is_relative_to(parent), 'Unsafe Stage20 cleanup target')
    if path.exists():
        regular_tree(path)
        shutil.rmtree(path)

@contextmanager
def host_trap(observed, executable):
    """Reuse the Stage19 host-process trap around all model-selected actions."""
    real = subprocess.Popen
    tree = ast.parse((ROOT/'agent_system/chatgpt_oauth.py').read_text())
    acl_scripts = {n.value for n in ast.walk(tree) if isinstance(n,ast.Constant)
        and isinstance(n.value,str) and n.value.startswith('$a=Get-Acl')}
    def trapped(argv,*args,**kw):
        name=Path(argv[0]).name.lower() if isinstance(argv,(list,tuple)) and argv else ''
        allowed=name in ('git','git.exe') or (name in ('docker','docker.exe') and list(argv[1:3])==['--context','desktop-linux'])
        if name=='codex.exe': allowed=Path(argv[0]).resolve()==Path(executable).resolve() and list(argv[1:])==['app-server','--listen','stdio://']
        if name.startswith('python'): allowed=len(argv)==6 and list(argv[1:4])==['-I','-c',CLEANUP]
        if name in ('powershell','powershell.exe'):
            allowed=len(argv)==5 and list(argv[1:4])==['-NoProfile','-NonInteractive','-Command'] and argv[4] in acl_scripts
        if not allowed:
            observed['host_execution_attempt']=True
            raise AgentSystemError('Unexpected host process denied')
        observed.setdefault('controller_host_process_names',set()).add(name)
        return real(argv,*args,**kw)
    subprocess.Popen=trapped
    try: yield
    finally: subprocess.Popen=real

def schema(properties):
    properties = {'task_id': {'type': 'string', 'const': TASK_ID},
                  'contract_version': {'type': 'integer', 'const': 1}, **properties}
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}

STR = {'type': 'string', 'minLength': 1, 'maxLength': 2000}
STRINGS = {'type': 'array', 'items': STR, 'maxItems': 20}
CONTRACT_SCHEMA = schema({'public_interface': {'const': TASK['public_interface'], 'type': 'string'},
    'acceptance_criteria': {'type': 'array', 'const': CRITERIA, 'items': STR},
    'allowed_mutation_scope': {'const': ['src/slugify.py'], 'type': 'array', 'items': STR},
    'constraints': STRINGS, 'risks': STRINGS})
IMPLEMENT_SCHEMA = schema({'outcome': {'type': 'string', 'enum': ['completed', 'failed']},
    'changed_files': {'type': 'array', 'items': {'enum': ['src/slugify.py'], 'type': 'string'}, 'maxItems': 1},
    'summary': STR, 'checks_run': STRINGS})
CASE_SCHEMA = {'type': 'object', 'properties': {'id': STR, 'intent': STR,
    'input': {'type': 'string', 'maxLength': 1000}, 'expected': {'type': 'string', 'maxLength': 1000}},
    'required': ['id', 'intent', 'input', 'expected'], 'additionalProperties': False}
DESIGN_SCHEMA = schema({'cases': {'type': 'array', 'minItems': 8, 'maxItems': 30, 'items': CASE_SCHEMA},
    'properties': {'type': 'array', 'uniqueItems': True, 'maxItems': 3,
        'items': {'type': 'string', 'enum': ['idempotence', 'output_shape', 'input_unchanged']}},
    'rationale': STR})
TEST_SCHEMA = schema({'outcome': {'type': 'string', 'enum': ['passed', 'failed']},
    'summary': STR, 'failures': STRINGS})
REVIEW_SCHEMA = schema({'recommendation': {'type': 'string', 'enum': ['accept', 'reject', 'request-fix']},
    'rationale': STR, 'unresolved_risks': STRINGS})

WRITE = "from pathlib import Path; import sys; p=Path('src/slugify.py'); p.write_text(sys.stdin.read(), encoding='utf-8'); print('written: src/slugify.py')"
INSPECT = "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text(encoding='utf-8'))"
CHECK = """import ast,inspect,json,pathlib,sys
p=pathlib.Path('src/slugify.py'); ast.parse(p.read_text()); compile(p.read_text(),str(p),'exec')
from src.slugify import slugify
s=inspect.signature(slugify)
assert list(s.parameters)==['value'] and s.parameters['value'].annotation in (str,'str') and s.return_annotation in (str,'str'), str(s)
cases=json.loads(sys.stdin.read() or '[]')
for v,e in cases: assert slugify(v)==e, (v,e,slugify(v))
print(json.dumps({'public_interface_verified':True,'own_cases_passed':len(cases)}))
"""

def acceptance_source(design):
    # Cases and property selection belong to the Tester, harness belongs to Controller.
    return '''import inspect,json,re,unittest
from src.slugify import slugify
DESIGN = json.loads(''' + repr(json.dumps(design)) + ''')
class Acceptance(unittest.TestCase):
    def test_interface(self):
        s=inspect.signature(slugify)
        self.assertEqual(list(s.parameters), ['value'])
        self.assertIn(s.parameters['value'].annotation, (str,'str'))
        self.assertIn(s.return_annotation, (str,'str'))
    def test_cases(self):
        for c in DESIGN['cases']:
            with self.subTest(case=c['id'], intent=c['intent']):
                self.assertEqual(slugify(c['input']), c['expected'])
    def test_properties(self):
        for c in DESIGN['cases']:
            v=c['input']; before=v; result=slugify(v)
            for prop in DESIGN['properties']:
                with self.subTest(case=c['id'], property=prop):
                    if prop=='idempotence': self.assertEqual(slugify(result), result)
                    elif prop=='output_shape': self.assertRegex(result, r'^(?:[a-z0-9]+(?:-[a-z0-9]+)*)?$')
                    elif prop=='input_unchanged': self.assertEqual(v, before)
if __name__=='__main__': unittest.main(verbosity=2)
'''

class Actions:
    """Task-specific selectors; never accepts model-selected raw executables."""
    def __init__(self, policy, permitted): self.policy, self.permitted = policy, permitted
    def resolve(self, request):
        from agent_system.model_tool_boundary import tool_spec
        p = self.policy
        require(isinstance(request, dict) and set(request) == set(tool_spec(p)['inputSchema']['required']), 'Unknown action arguments')
        require(all(request.get(k) == v and type(request.get(k)) is type(v) for k,v in p.identity().items()), 'Stage20 action identity mismatch')
        argv = request.get('argv')
        require(isinstance(argv, list) and len(argv) >= 1 and argv[0] in self.permitted, 'Unapproved Stage20 action')
        action = argv[0]
        commands = {'write': ['python', '-c', WRITE], 'check': ['python', '-c', CHECK],
                    'acceptance': ['python', '-m', 'unittest', 'tests.test_acceptance', '-v'],
                    'status': ['git', 'diff', '--', 'src/slugify.py']}
        if action == 'inspect':
            require(len(argv) == 2 and argv[1] in ('src/slugify.py', 'TASK.json'), 'Unowned inspection path')
            command = ['python', '-c', INSPECT, argv[1]]
        else:
            require(argv == (['write', 'src/slugify.py'] if action == 'write' else [action]), 'Unexpected selector arguments')
            command = commands[action]
        require(request.get('read_only') is (action != 'write'), 'Stage20 read-only escalation')
        require(request.get('tool_type') == 'argv', 'Unknown privileged tool')
        if action == 'check':
            cases = strict_json(request['stdin'] or '[]')
            require(isinstance(cases, list) and len(cases) <= 30 and all(isinstance(c,list) and len(c)==2 and all(isinstance(s,str) and len(s)<=1000 for s in c) for c in cases), 'Invalid own-check cases')
        elif action != 'write': require(request['stdin'] == '', 'Unexpected action input')
        return {**request, 'argv': command}

class ActionBridge(IsolatedExecutionBridge):
    def __init__(self, *args, actions, **kw):
        super().__init__(*args, **kw)
        self.actions, self.evidence = actions, []
    def execute(self, request):
        resolved = self.actions.resolve(request)
        before = file_map(self.workspace)
        result = super().execute(resolved)
        after = file_map(self.workspace)
        paths = sorted(k for k in before.keys() | after.keys() if before.get(k) != after.get(k))
        require(set(paths) <= ({'src/slugify.py'} if request['argv'][0]=='write' else set()), 'Unexpected project mutation')
        self.evidence.append({'action': request['argv'], 'read_only': request['read_only'],
            'changed_paths': paths, **result})
        return result

class ActionGate(ResponsesGate):
    def __init__(self, *args, actions, **kw):
        super().__init__(*args, **kw); self.actions=actions
    def request(self, raw):
        value = super().request(raw)
        value['parallel_tool_calls'] = False
        if not self.actions.permitted: value['tool_choice'] = 'none'
        value['tools'][0]['tools'][0]['description'] = 'Controller task actions only: ' + ', '.join(self.actions.permitted) + '. No raw argv, shells or Python commands. write uses argv=["write","src/slugify.py"] and stdin=complete source; check uses argv=["check"] and stdin=JSON [[input,expected],...]; inspect uses argv=["inspect","src/slugify.py"] or ["inspect","TASK.json"]; status uses argv=["status"]; acceptance uses argv=["acceptance"]. Only write has read_only=false; every other action has read_only=true and empty stdin except check. All identity fields must match the schema. Choose timeout_seconds=20 and output_bytes=65536.'
        return value
    def inspect_response(self, raw):
        result = super().inspect_response(raw)
        for canonical in result[0].values(): self.actions.resolve(strict_json(canonical))
        return result

class UsageSession(CodexToolSession):
    def handle(self, value):
        if value.get('method') == 'thread/tokenUsage/updated':
            usage = value.get('params', {}).get('tokenUsage', {})
            # Numeric fields only; do not persist provider identifiers or text.
            self.usage = {k: {n:v for n,v in section.items() if type(v) in (int,float)}
                          for k,section in usage.items() if isinstance(section,dict)}
        super().handle(value)

def prepare():
    import yaml
    require(not OWNED.exists(), 'Stage20 disposable repository already exists')
    old = load(ROOT/'docs/stage19g-smoke-8-evidence/fresh-admission.json')
    old_runner = ToolDockerRunner(Configuration.load(Path(old['project'])))
    require(old_runner.preflight() == old['binding'], 'Accepted Stage19 binding changed')
    old_runner.require_transport_admission()
    old_store = old_runner._store()
    validation = old_store.verify('validation')
    transport = old_store.verify('stage18c-transport')
    project = OWNED/'project'; project.mkdir(parents=True)
    shutil.copytree(ROOT/'.agent_system', project/'.agent_system')
    conf = yaml.safe_load((Path(old['project'])/'.agent_system/project.yaml').read_text())
    conf['runtime'] = {'version':2,'root':str(OWNED/'runtime')}
    (project/'.agent_system/project.yaml').write_text(yaml.safe_dump(conf))
    (project/'src').mkdir()
    (project/'src/slugify.py').write_text('def slugify(value: str) -> str:\n    raise NotImplementedError\n')
    atomic_json(project/'TASK.json', TASK)
    (project/'.gitignore').write_text('__pycache__/\n*.pyc\n')
    git(project,'init','--initial-branch=main'); git(project,'config','user.name','Stage20 Controller')
    git(project,'config','user.email','stage20@example.invalid'); git(project,'add','.')
    git(project,'commit','-m','Freeze Stage20 slugify task and baseline')
    config=Configuration.load(project); runner=ToolDockerRunner(config)
    new_binding=runner.preflight()
    require({k:v for k,v in new_binding.items() if k!='project'} == {k:v for k,v in old['binding'].items() if k!='project'}, 'Containment implementation/runtime changed')
    # Adopt already verified evidence for the identical engine/image/implementation.
    # Rebind project ownership; do not claim fresh adversarial probes.
    new_store=runner._store(); new_store.directory.mkdir(parents=True,exist_ok=True)
    for cap in validation['capabilities'].values():
        for name, expected in cap.get('evidence',[]):
            src=old_store.directory/name; dst=new_store.directory/name
            require(sha(src)==expected, 'Inherited isolation evidence changed')
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    new_store.issue('validation', validation)
    shutil.copyfile(old_store.directory/'stage18c-proof.json',new_store.directory/'stage18c-proof.json')
    new_store.issue('stage18c-transport', transport)
    runner.require_transport_admission()
    base=git(project,'rev-parse','HEAD'); manifest={'task_id':TASK_ID,'base_commit':base,'worktrees':{}}
    for name in ('orchestrator','implementer','tester','reviewer'):
        workspace=config.worktrees_dir/TASK_ID/name
        IsolatedCheckout.create(project,workspace,base,config.runs_dir/TASK_ID/'controller'/name)
        manifest['worktrees'][name]={'path':str(workspace),'kind':'isolated_checkout'}
    atomic_json(config.runs_dir/TASK_ID/'worktrees.json',manifest)
    save('prepared', {'project':str(project),'binding':new_binding,'manifest':manifest,
        'inherited_admission':True,'fresh_adversarial_probes':False,'source':str(old_store.directory),
        'task_sha256':sha(project/'TASK.json'),'driver_sha256':sha(Path(__file__))})
    save('frozen-task',TASK)
    print('Fresh Controller-owned repository prepared; accepted transport unchanged.',flush=True)

class Workflow:
    def __init__(self):
        self.prepared=load(OUT/'prepared.json'); self.config=Configuration.load(Path(self.prepared['project']))
        self.runner=ToolDockerRunner(self.config); self.records=[]
        self.task={**TASK,'scope':{'allowed_paths':['src/slugify.py'],'forbidden_paths':[]},
            'workflow':{'test_paths':['tests/test_acceptance.py']}}
        self.store=CredentialStore(Path('C:/Users/4ivan/.agentctl/stage19-oauth'),[ROOT])
        credentials=self.store.read('credentials.json')
        require(credentials['expires_at']-time.time()>180,'Expired plan connection')
        self.secrets=SecretFilter([credentials[k] for k in ('access_token','refresh_token','id_token')])
        self.credentials_hashes={p.name:sha(p) for p in self.store.directory.iterdir() if p.is_file()}
        self.client_id=credentials['client_id']
        self.confirmed_at=load(ROOT/'docs/stage19g-smoke-8-evidence/authorization.json')['human_billing_confirmation_at']
        self.production_before={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'agent_system').rglob('*.py')}
        self.driver_hash=sha(Path(__file__))
    def workspace(self,name): return Path(self.prepared['manifest']['worktrees'][name]['path'])
    def admission(self):
        require(sha(Path(__file__))==self.driver_hash,'Workflow driver changed')
        require(self.runner.preflight()==self.prepared['binding'],'Stage20 containment binding changed')
        self.runner.require_transport_admission()
    def role(self,label,role,phase,name,bundle,instruction,result_schema,permitted):
        model,effort=ROUTES[role]; workspace=self.workspace(name)
        policy=ExecutionPolicy(InvocationBinding('stage20-'+label,role,TASK_ID,1,model,effort),
            phase,hashlib.sha256(str(workspace.resolve()).encode()).hexdigest(),time.monotonic()+300,
            max_requests=7 if permitted else 1,max_tool_calls=6,max_tool_seconds=20,output_bytes=65536)
        approvals=ApprovalStore(self.config.runtime_root/'workflow-approvals'/label,
            {'binding':self.prepared['binding'],'driver':self.driver_hash,'context':hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest()})
        approvals.issue('no-credits/'+policy.binding.execution_id,{'execution_id':policy.binding.execution_id,
            'client_id':self.client_id,'credits_fallback_disabled':True,'operator':'Existing human OFF preference retained',
            'attested_at':self.confirmed_at})
        approvals.issue('live-smoke/'+policy.binding.execution_id,{'authorized':True,**policy.identity(),
            'model':model,'reasoning':effort,'route':UPSTREAM})
        actions=Actions(policy,permitted); bridge=ActionBridge(self.runner,workspace,self.task,policy,self.secrets,actions=actions)
        gate=ActionGate(policy,self.secrets,actions=actions)
        upstream=PlanUpstream(self.store,policy,approvals,self.admission,self.runner.cancel_event)
        prompt=instruction+'\nExplicit handoff bundle:\n'+json.dumps(bundle)+'\nReturn ONLY JSON matching this result schema: '+json.dumps(result_schema)
        self.secrets.reject(prompt)
        save(label+'-context',{'identity':policy.identity(),'model':model,'reasoning':effort,'bundle':bundle,
            'instruction':instruction,'result_schema':result_schema,'previous_conversation_visible':False})
        record={'label':label,**policy.identity(),'model':model,'reasoning':effort,'completed':False,'requests':0,'tool_calls':0}
        self.records.append(record); save('role-counts',self.records)
        exe=self.prepared['binding']['stage18c']['codex']; home=self.config.runtime_root/'model-homes'/label
        session=None; started=time.monotonic()
        print('Starting '+label+' ('+model+'/'+effort+')',flush=True)
        try:
            with host_trap(record,exe['path']):
                with LocalModelRelay(gate,upstream) as relay:
                    session=UsageSession(Path(exe['path']),exe['sha256'],home,relay,bridge,policy)
                    with session: result=session.run(prompt,result_schema)
                    private=SecretFilter([relay.child_channel()])
                    for p in home.rglob('*'):
                        if p.is_file(): private.reject(p.read_bytes().decode('utf-8',errors='replace'))
            save(label+'-result',result); record['completed']=True
            return result
        finally:
            bridge.close()
            if session: session.close()
            record.update(requests=gate.requests,tool_calls=bridge.calls,seconds=round(time.monotonic()-started,2),
                usage=getattr(session,'usage',None),process_exited=bool(session and session.process and session.process.poll() is not None),
                gate_observations=gate.response_metadata_history,transport_observations=upstream.response_metadata_history,
                session_observations=getattr(session,'observation_metadata',{}))
            record['controller_host_process_names']=sorted(record.get('controller_host_process_names',[]))
            save(label+'-tools',bridge.evidence); save('role-counts',self.records)
            remove_owned(home,self.config.runtime_root)
            print('Finished '+label+': '+str(record['completed'])+', '+str(gate.requests)+' requests, '+str(bridge.calls)+' tools',flush=True)

def run():
    with (OUT/'one-workflow.consumed').open('x') as f: f.write('Exactly one Stage20 workflow; no automatic restart.\n')
    workflow=Workflow(); w=workflow
    assessment={'task_id':TASK_ID,'accepted':False,'verdict':'FAIL_WORKFLOW_COORDINATION','fix_cycles':0,
        'routing':{r:{'model':m,'reasoning':e} for r,(m,e) in ROUTES.items()},'roles':[], 'capability_violations':[]}
    stage='architecture'
    try:
        catalog=load(OUT/'catalog.json')
        require(all(any(m['model']==model and effort in m['reasoning'] for m in catalog['models']) for model,effort in ROUTES.values()),'Requested routing unavailable')
        w.admission()
        contract=w.role('architect','orchestrator','architecture','orchestrator',{'task':TASK},
            'Act as Architect. Produce a compact useful contract and risks. Copy frozen acceptance criteria exactly. Only src/slugify.py may change. Do not implement code or use tools.',CONTRACT_SCHEMA,[])
        stage='implementation'
        implementation=w.role('implementer','implementer','implementation','implementer',{'task':TASK,'contract':contract},
            'Implement slugify in the owned Docker workspace. Use write then check with useful self-chosen cases; inspect/status if useful. No raw commands. Do not claim success without successful write/check results. Finish with compact implementation handoff.',IMPLEMENT_SCHEMA,['inspect','write','check','status'])
        candidate=w.workspace('implementer')/'src/slugify.py'
        (OUT/'candidate').mkdir(); shutil.copyfile(candidate,OUT/'candidate/slugify.py')
        before=file_map(w.workspace('orchestrator')); after=file_map(w.workspace('implementer'))
        changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
        assessment['changed_files']=changed
        require(changed==['src/slugify.py'] and implementation['outcome']=='completed' and implementation['changed_files']==changed,'Implementer result/scope mismatch')
        diff=git(w.workspace('implementer'),'diff','--','src/slugify.py')
        (OUT/'final.diff').write_text(diff,encoding='utf-8')
        stage='test_design'
        design=w.role('test-design','test_engineer','test_design','tester',{'task':TASK,'contract':contract},
            'Independently design 8-30 meaningful acceptance/adversarial cases covering all requirements and tricky interactions. You have only the baseline and task/contract; no candidate or implementer context. Freeze expected input/output pairs and useful optional properties. Do not use tools or implement the utility.',DESIGN_SCHEMA,[])
        require(len({c['id'] for c in design['cases']})==len(design['cases']),'Duplicate test IDs')
        require(all(c['input'].isascii() and c['expected'].isascii() for c in design['cases']),'Tests exceed ASCII scope')
        save('test-freeze',{'design_sha256':sha(OUT/'test-design-result.json'),'frozen_at':time.time(),
            'candidate_visible_during_design':False,'test_intent_frozen_before_candidate_exposure':True})
        tester=w.workspace('tester'); (tester/'tests').mkdir()
        (tester/'tests/__init__.py').write_text('')
        (tester/'tests/test_acceptance.py').write_text(acceptance_source(design),encoding='utf-8')
        shutil.copyfile(tester/'tests/test_acceptance.py',OUT/'independent_tests.py')
        test_hash=sha(tester/'tests/test_acceptance.py')
        shutil.copyfile(candidate,tester/'src/slugify.py')
        stage='testing'
        test_result=w.role('test-execution','test_engineer','test_implementation','tester',{'task':TASK,
            'contract':contract,'frozen_design':design,'design_sha256':sha(OUT/'test-design-result.json')},
            'Execute the already frozen independent tests against the candidate now present in your workspace. Use acceptance once; inspect candidate if needed. No edits, no new cases, no implementer context. Report actual pass/fail and failures.',TEST_SCHEMA,['acceptance','inspect'])
        test_tools=load(OUT/'test-execution-tools.json')
        executed=[t for t in test_tools if t['action']==['acceptance']]
        require(len(executed)==1,'Tester did not execute frozen acceptance suite exactly once')
        require(sha(tester/'tests/test_acceptance.py')==test_hash and sha(candidate)==sha(tester/'src/slugify.py'),'Frozen tests/candidate changed')
        assessment['tests']={'cases':len(design['cases']),'properties':design['properties'],
            'passed':executed[0]['returncode']==0,'result':test_result,'evidence':executed[0]}
        require(test_result['outcome']==('passed' if assessment['tests']['passed'] else 'failed'),'Tester handoff contradicts execution')
        stage='review'
        review=w.role('reviewer','reviewer','review','reviewer',{'task':TASK,'contract':contract,'final_diff':diff,
            'implementation_result':implementation,'implementer_checks':load(OUT/'implementer-tools.json'),
            'test_design':design,'test_result':test_result,'test_evidence':executed[0]},
            'Review only. Evaluate final diff, interface, frozen contract and independent evidence. Give accept/reject/request-fix with concise rationale and unresolved risks. Do not edit files or use tools.',REVIEW_SCHEMA,[])
        assessment['review']=review
        stage='acceptance'
        public=w.runner.run_tool(['python','-c',CHECK],tester,w.task,'test_engineer','test_implementation',True,'[]',20)
        save('controller-interface-check',{'returncode':public.returncode,'stdout':public.stdout,'stderr':public.stderr})
        own=[t for t in load(OUT/'implementer-tools.json') if t['action']==['check']]
        assessment['accepted']=bool(public.returncode==0 and own and all(t['returncode']==0 for t in own)
            and assessment['tests']['passed'] and review['recommendation']=='accept')
        if assessment['accepted']:
            shutil.copyfile(candidate,w.config.root/'src/slugify.py')
            git(w.config.root,'add','src/slugify.py'); git(w.config.root,'commit','-m','Accept Stage20 independently tested slugify')
            assessment['accepted_commit']=git(w.config.root,'rev-parse','HEAD')
        assessment['verdict']='PASS_MULTI_AGENT_WORKFLOW' if assessment['accepted'] else 'FAIL_PROJECT_RESULT'
    except BaseException as error:
        # Failure categories stay separate; no transport redesign or automatic retry.
        message=str(error)
        security=('identity','Unapproved','Unowned','read-only','privileged','Credential','Builtin','Built-in','host process')
        if any(s in message for s in security):
            assessment['verdict']='FAIL_CAPABILITY_BOUNDARY'; assessment['capability_violations'].append(message[:500])
        elif stage in ('acceptance','testing') or 'result/scope' in message: assessment['verdict']='FAIL_PROJECT_RESULT'
        assessment['failed_stage']=stage
        assessment['failure_type']=type(error).__name__
        assessment['failure_reason']=w.secrets.redact(message)[:1000]
    finally:
        assessment['roles']=w.records
        assessment['containment']={'production_source_unchanged':w.production_before=={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'agent_system').rglob('*.py')},
            'credential_store_unchanged':w.credentials_hashes=={p.name:sha(p) for p in w.store.directory.iterdir() if p.is_file()},
            'stale_owned_containers':len(w.runner.stale_executions()),'model_homes_removed':not any((w.config.runtime_root/'model-homes').glob('*')),
            'role_network':'none','host_fallback':False,'independent_context_before_candidate':(OUT/'test-freeze.json').exists()}
        records=[load(p) for p in w.runner.root.glob('executions/*/ownership.json')]
        assessment['containment']['docker_cleanup_confirmed']=all(r.get('cleanup')=='confirmed' and r.get('storage_cleanup')=='confirmed' for r in records)
        assessment['controller_checks']=1 if (OUT/'controller-interface-check.json').exists() else 0
        if not all(assessment['containment'][k] for k in ('production_source_unchanged','credential_store_unchanged','model_homes_removed','docker_cleanup_confirmed')) or assessment['containment']['stale_owned_containers']:
            assessment['accepted']=False; assessment['verdict']='FAIL_CAPABILITY_BOUNDARY'
        # Preserve handoffs, tests, diff and accepted repository; dispose role storage.
        try:
            remove_owned(w.config.runtime_root,OWNED/'runtime')
            assessment['containment']['disposable_role_storage_removed']=not w.config.runtime_root.exists()
        except BaseException:
            assessment['accepted']=False; assessment['verdict']='FAIL_CAPABILITY_BOUNDARY'
            assessment['containment']['disposable_role_storage_removed']=False
        save('assessment',assessment)
        for p in OUT.rglob('*'):
            if p.is_file(): w.secrets.reject(p.read_bytes().decode('utf-8',errors='replace'))
        print(json.dumps({'verdict':assessment['verdict'],'accepted':assessment['accepted'],'failed_stage':assessment.get('failed_stage')}),flush=True)
    return 0 if assessment['accepted'] else 1

if __name__=='__main__':
    require(sys.argv[1:] in (['--prepare'],['--run-once']),'Explicit Stage20 entry required')
    OUT.mkdir(parents=True,exist_ok=True)
    if sys.argv[1]=='--prepare': prepare()
    else: raise SystemExit(run())
