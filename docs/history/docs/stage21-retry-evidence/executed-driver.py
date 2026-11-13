"""One task-specific live workflow. Stage19 transport is imported unchanged."""
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
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

OUT = ROOT / 'docs/stage21-retry-evidence'
OWNED = ROOT / '.test-tmp/stage21-workflow-retry'
TASK_ID = 'STAGE20-LABELS'
ROUTES = {'orchestrator': ('gpt-6-astra', 'medium'),
          'implementer': ('gpt-5.6-sol', 'high'),
          'test_engineer': ('gpt-5.6-sol', 'high'), 'reviewer': ('gpt-6-astra', 'medium')}
CRITERIA = [
    'Scan ASCII strings left to right. An unescaped comma outside double quotes ends a label; repeated separators are allowed.',
    'An unescaped double quote toggles quoted mode anywhere within a label; quote delimiters are removed and adjacent quoted/unquoted text concatenates.',
    'Backslash escapes exactly the next character in either mode: remove the backslash, preserve the next character literally, and do not treat it as a quote or separator.',
    'A trailing unpaired backslash or unclosed double quote raises ValueError for the whole input, even after otherwise valid labels.',
    'Only ASCII whitespace (space, tab, CR, LF, vertical tab, form feed) that was neither quoted nor escaped is ordinary whitespace.',
    'Trim ordinary whitespace from each label boundary before collapsing internal ordinary-whitespace runs to one ASCII space.',
    'Quoted or escaped whitespace is protected: preserve its exact characters and multiplicity, including at label boundaries; it also breaks ordinary-whitespace runs.',
    'Lowercase ASCII A-Z in all emitted characters; preserve other non-delimiter literal characters exactly.',
    'After parsing and normalization, discard labels whose resulting string is empty. Whitespace-only protected labels are nonempty and retained.',
    'Deduplicate normalized strings by exact equality, retaining first occurrence order. Empty input returns an empty list.'
]
TASK = {'task_id': TASK_ID, 'contract_version': 1,
    'public_interface': 'def normalize_labels(value: str) -> list[str]',
    'file': 'src/normalize_labels.py', 'acceptance_criteria': CRITERIA,
    'constraints': ['Pure Python, standard library only, no external dependencies or I/O.',
        'ASCII string inputs are in scope; Unicode and non-string behavior are unspecified.',
        'Do not add features or mutate any file other than src/normalize_labels.py.']}
REPAIR_LIMIT = 2  # Existing Workflow ceiling; a configured usage ceiling can lower it.

def require(ok, message):
    if not ok: raise AgentSystemError(message)

def load(path): return strict_json(path.read_text(encoding='utf-8'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value): atomic_json(OUT / (name + '.json'), value)

def production_hashes():
    return {p.relative_to(ROOT).as_posix():sha(p) for directory in (ROOT/'agent_system', ROOT/'.agent_system')
        for p in directory.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc'}

def remove_owned(path, parent):
    path, parent = path.resolve(), parent.resolve()
    require(path != parent and path.is_relative_to(parent), 'Unsafe Stage21 cleanup target')
    if path.exists():
        regular_tree(path)
        def clear_readonly(function, filename, exc_info):
            candidate=Path(filename)
            require(candidate.resolve().is_relative_to(path) and not candidate.is_symlink(), 'Unsafe readonly cleanup target')
            if not isinstance(exc_info[1],PermissionError): raise exc_info[1]
            candidate.chmod(stat.S_IREAD|stat.S_IWRITE)
            function(filename)
        shutil.rmtree(path,onerror=clear_readonly)

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
    'allowed_mutation_scope': {'const': ['src/normalize_labels.py'], 'type': 'array', 'items': STR},
    'constraints': STRINGS, 'risks': STRINGS})
IMPLEMENT_SCHEMA = schema({'outcome': {'type': 'string', 'enum': ['completed', 'failed']},
    'changed_files': {'type': 'array', 'items': {'enum': ['src/normalize_labels.py'], 'type': 'string'}, 'maxItems': 1},
    'summary': STR, 'checks_run': STRINGS, 'uncertainty': {'type':'string','maxLength':2000}})
CASE_SCHEMA = {'type': 'object', 'properties': {'id': STR, 'intent': STR,
    'input': {'type': 'string', 'maxLength': 1000},
    'expected': {'type': ['array','null'], 'items': {'type':'string','maxLength':1000}, 'maxItems':100}},
    'required': ['id', 'intent', 'input', 'expected'], 'additionalProperties': False}
DESIGN_SCHEMA = schema({'cases': {'type': 'array', 'minItems': 10, 'maxItems': 24, 'items': CASE_SCHEMA},
    'properties': {'type': 'array', 'uniqueItems': True, 'maxItems': 2,
        'items': {'type': 'string', 'enum': ['unique_nonempty_labels', 'ascii_lowercase']}},
    'rationale': STR})

REVIEW_SCHEMA = schema({'recommendation': {'type': 'string', 'enum': ['accept', 'reject', 'request-fix']},
    'rationale': STR, 'unresolved_risks': STRINGS})

WRITE = "from pathlib import Path; import sys; p=Path('src/normalize_labels.py'); p.write_text(sys.stdin.read(), encoding='utf-8'); print('written: src/normalize_labels.py')"
INSPECT = "from pathlib import Path; import sys; print(Path(sys.argv[1]).read_text(encoding='utf-8'))"
CHECK = """import ast,inspect,json,pathlib,sys
p=pathlib.Path('src/normalize_labels.py'); ast.parse(p.read_text()); compile(p.read_text(),str(p),'exec')
from src.normalize_labels import normalize_labels
s=inspect.signature(normalize_labels)
assert list(s.parameters)==['value'] and s.parameters['value'].annotation in (str,'str') and s.return_annotation in (list[str],'list[str]'), str(s)
cases=json.loads(sys.stdin.read() or '[]')
for v,e in cases:
    if e is None:
        try: normalize_labels(v)
        except ValueError: pass
        else: raise AssertionError(('Expected ValueError',v))
    else:
        actual=normalize_labels(v)
        assert actual==e, (v,e,actual)
print(json.dumps({'public_interface_verified':True,'own_cases_passed':len(cases)}))
"""

def acceptance_source(design):
    # Only the frozen Tester data selects cases, expectations and properties.
    return '''import inspect,json,sys
from src.normalize_labels import normalize_labels
DESIGN = json.loads(''' + repr(json.dumps(design)) + ''')
results=[]; properties=[]; interface=True
s=inspect.signature(normalize_labels)
interface=(list(s.parameters)==['value'] and s.parameters['value'].annotation in (str,'str') and s.return_annotation in (list[str],'list[str]'))
for c in DESIGN['cases']:
    actual=None; error=None
    try: actual=normalize_labels(c['input'])
    except Exception as exc: error=type(exc).__name__
    passed=(error=='ValueError') if c['expected'] is None else (error is None and type(actual) is list and actual==c['expected'])
    results.append({'id':c['id'],'input':c['input'],'expected':c['expected'],'actual':actual,'error':error,'passed':passed})
    if error is None and type(actual) is list:
        for prop in DESIGN['properties']:
            ok=(all(type(x) is str and x!='' for x in actual) and len(actual)==len(set(actual))) if prop=='unique_nonempty_labels' else all(type(x) is str and not any('A'<=ch<='Z' for ch in x) for x in actual)
            properties.append({'case':c['id'],'property':prop,'passed':ok})
passed=interface and all(c['passed'] for c in results) and all(c['passed'] for c in properties)
print(json.dumps({'passed':passed,'interface':interface,'cases':results,'properties':properties},ensure_ascii=True))
sys.exit(0 if passed else 1)
'''

def contract_interpret(value):
    """Controller contract-consistency check; never supplies acceptance expectations.
    Written before the run; used only to classify a failing frozen case."""
    tokens=[]; current=[]; quoted=False; escape=False
    for ch in value:
        if escape:
            current.append((ch,True)); escape=False
        elif ch==chr(92): escape=True
        elif ch=='"': quoted=not quoted
        elif ch==',' and not quoted: tokens.append(current); current=[]
        else: current.append((ch,quoted))
    if escape or quoted: raise ValueError()
    tokens.append(current); result=[]
    ordinary=lambda item: not item[1] and item[0] in ' \t\r\n\v\f'
    for token in tokens:
        while token and ordinary(token[0]): token=token[1:]
        while token and ordinary(token[-1]): token=token[:-1]
        chars=[]; in_run=False
        for ch,protected in token:
            if ordinary((ch,protected)):
                if not in_run: chars.append(' ')
                in_run=True
            else:
                chars.append(chr(ord(ch)+32) if 'A'<=ch<='Z' else ch); in_run=False
        label=''.join(chars)
        if label and label not in result: result.append(label)
    return result

def classify_failures(execution, design):
    by_id={c['id']:c for c in design['cases']}
    classified=[]
    for failure in execution['cases']:
        if failure['passed']: continue
        c=by_id[failure['id']]
        try: expected=contract_interpret(c['input'])
        except ValueError: expected=None
        kind='implementation_defect' if expected==c['expected'] else 'test_defect'
        classified.append({**failure,'classification':kind,'contract_expected':expected,
            'basis':'Contract rules 1-10; Controller interpreter preserved in executed-driver.py before candidate creation.'})
    if not execution['interface'] or any(not p['passed'] for p in execution['properties']):
        classified.append({'classification':'implementation_defect','basis':'Required interface or selected contract-derived output invariant failed.'})
    return classified

class Actions:
    """Task-specific selectors; never accepts model-selected raw executables."""
    def __init__(self, policy, permitted): self.policy, self.permitted = policy, permitted
    def resolve(self, request):
        from agent_system.model_tool_boundary import tool_spec
        p = self.policy
        require(isinstance(request, dict) and set(request) == set(tool_spec(p)['inputSchema']['required']), 'Unknown action arguments')
        require(all(request.get(k) == v and type(request.get(k)) is type(v) for k,v in p.identity().items()), 'Stage21 action identity mismatch')
        argv = request.get('argv')
        require(isinstance(argv, list) and len(argv) >= 1 and argv[0] in self.permitted, 'Unapproved Stage21 action')
        action = argv[0]
        commands = {'write': ['python', '-c', WRITE], 'check': ['python', '-c', CHECK],
                    'acceptance': ['python', '-m', 'unittest', 'tests.test_acceptance', '-v'],
                    'status': ['git', 'diff', '--', 'src/normalize_labels.py']}
        if action == 'inspect':
            require(len(argv) == 2 and argv[1] in ('src/normalize_labels.py', 'TASK.json'), 'Unowned inspection path')
            command = ['python', '-c', INSPECT, argv[1]]
        else:
            require(argv == (['write', 'src/normalize_labels.py'] if action == 'write' else [action]), 'Unexpected selector arguments')
            command = commands[action]
        require(request.get('read_only') is (action != 'write'), 'Stage21 read-only escalation')
        require(request.get('tool_type') == 'argv', 'Unknown privileged tool')
        if action == 'check':
            cases = strict_json(request['stdin'] or '[]')
            require(isinstance(cases, list) and len(cases) <= 30 and all(isinstance(c,list) and len(c)==2 and isinstance(c[0],str) and len(c[0])<=1000 and (c[1] is None or isinstance(c[1],list) and all(isinstance(s,str) and len(s)<=1000 for s in c[1])) for c in cases), 'Invalid own-check cases')
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
        require(set(paths) <= ({'src/normalize_labels.py'} if request['argv'][0]=='write' else set()), 'Unexpected project mutation')
        self.evidence.append({'action': request['argv'], 'read_only': request['read_only'],
            'changed_paths': paths, 'self_check_cases':strict_json(request['stdin'] or '[]') if request['argv'][0]=='check' else None, **result})
        return result

class ActionGate(ResponsesGate):
    def __init__(self, *args, actions, **kw):
        super().__init__(*args, **kw); self.actions=actions
    def request(self, raw):
        value = super().request(raw)
        value['parallel_tool_calls'] = False
        if not self.actions.permitted: value['tool_choice'] = 'none'
        value['tools'][0]['tools'][0]['description'] = 'Controller task actions only: ' + ', '.join(self.actions.permitted) + '. No raw argv, shells or Python commands. write uses argv=["write","src/normalize_labels.py"] and stdin=complete source; check uses argv=["check"] and stdin=JSON [[input,expected],...]; inspect uses argv=["inspect","src/normalize_labels.py"] or ["inspect","TASK.json"]; status uses argv=["status"]; acceptance uses argv=["acceptance"]. Only write has read_only=false; every other action has read_only=true and empty stdin except check. All identity fields must match the schema. Choose timeout_seconds=20 and output_bytes=65536.'
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
    require(not OWNED.exists(), 'Stage21 disposable repository already exists')
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
    (project/'src/normalize_labels.py').write_text('def normalize_labels(value: str) -> list[str]:\n    raise NotImplementedError\n')
    atomic_json(project/'TASK.json', TASK)
    (project/'.gitignore').write_text('__pycache__/\n*.pyc\n')
    git(project,'init','--initial-branch=main'); git(project,'config','user.name','Stage21 Controller')
    git(project,'config','user.email','stage21@example.invalid'); git(project,'add','.')
    git(project,'commit','-m','Freeze Stage21 label-parser contract and baseline')
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
        self.task={**TASK,'scope':{'allowed_paths':['src/normalize_labels.py'],'forbidden_paths':[]},
            'workflow':{'test_paths':['tests/test_acceptance.py']}}
        self.store=CredentialStore(Path('C:/Users/4ivan/.agentctl/stage19-oauth'),[ROOT])
        credentials=self.store.read('credentials.json')
        require(credentials['expires_at']-time.time()>180,'Expired plan connection')
        self.secrets=SecretFilter([credentials[k] for k in ('access_token','refresh_token','id_token')])
        self.credentials_hashes={p.name:sha(p) for p in self.store.directory.iterdir() if p.is_file()}
        self.client_id=credentials['client_id']
        self.confirmed_at=load(ROOT/'docs/stage19g-smoke-8-evidence/authorization.json')['human_billing_confirmation_at']
        self.production_before=production_hashes()
        save('production-before',self.production_before)
        save('credential-baseline',{'taken_at':time.time(),'file_sha256':self.credentials_hashes,
            'scope':'After user-authorized prerequisite reconnection; unchanged throughout Stage21 workflow'})
        self.driver_hash=sha(Path(__file__))
    def workspace(self,name): return Path(self.prepared['manifest']['worktrees'][name]['path'])
    def admission(self):
        require(sha(Path(__file__))==self.driver_hash,'Workflow driver changed')
        require(self.runner.preflight()==self.prepared['binding'],'Stage21 containment binding changed')
        self.runner.require_transport_admission()
    def role(self,label,role,phase,name,bundle,instruction,result_schema,permitted):
        model,effort=ROUTES[role]; workspace=self.workspace(name)
        policy=ExecutionPolicy(InvocationBinding('stage21-retry-'+label,role,TASK_ID,1,model,effort),
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

def controller_execute(w, tester, design, candidate, epoch):
    w.admission()
    before=file_map(tester)
    frozen=load(OUT/'test-freeze.json')
    candidate_hash=sha(candidate)
    require(sha(OUT/'test-design-result.json')==frozen['design_sha256'], 'Frozen design changed')
    require(sha(tester/'tests/test_acceptance.py')==frozen['harness_sha256'], 'Frozen harness changed')
    require(sha(tester/'src/normalize_labels.py')==candidate_hash, 'Exposed candidate mismatch')
    observed={}
    exe=w.prepared['binding']['stage18c']['codex']
    with host_trap(observed,exe['path']):
        cp=w.runner.run_tool(['python','-m','tests.test_acceptance'],tester,w.task,
            'test_engineer','test_implementation',True,'',20)
    require(file_map(tester)==before and sha(candidate)==candidate_hash, 'Acceptance mutated frozen workspace')
    result=strict_json(cp.stdout.strip())
    require(result['passed']==(cp.returncode==0), 'Acceptance status contradicts process')
    record={'epoch':epoch,'design_sha256':frozen['design_sha256'],'harness_sha256':frozen['harness_sha256'],
        'candidate_sha256_before':candidate_hash,'candidate_sha256_after':sha(candidate),
        'executed_at':time.time(),'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,
        'host_observation':{k:sorted(v) if isinstance(v,set) else v for k,v in observed.items()},
        'result':result,'model_requests':0,'tester_sessions':0}
    save('acceptance-'+str(epoch),record)
    return record

def mutation_scope(w):
    before=file_map(w.workspace('orchestrator')); after=file_map(w.workspace('implementer'))
    changed=sorted(p for p in before.keys()|after.keys() if before.get(p)!=after.get(p))
    require(changed==['src/normalize_labels.py'], 'Implementer mutation scope mismatch')
    return {'changed_files':changed,'allowed_paths':['src/normalize_labels.py'],'passed':True}

def run():
    w=Workflow()
    w.admission()
    catalog=load(OUT/'catalog.json')
    require(catalog['credentials_valid'] and all(any(m['model']==model and effort in m['reasoning']
        for m in catalog['models']) for model,effort in ROUTES.values()),'Stage20 routing unavailable')
    with (OUT/'one-workflow.consumed').open('x') as f:
        f.write('Exactly one Stage21 workflow; no automatic restart.\n')
    shutil.copyfile(Path(__file__),OUT/'executed-driver.py')
    limit=min(REPAIR_LIMIT,w.config.project.get('usage_limits',{}).get('max_autonomous_fix_cycles',REPAIR_LIMIT))
    assessment={'task_id':TASK_ID,'accepted':False,'verdict':'FAIL_WORKFLOW_COORDINATION','fix_cycles':0,
        'repair_limit':limit,'repair_limit_source':'agent_system/workflow.py existing two-cycle ceiling, lowered by configured usage limit if present',
        'routing':{r:{'model':m,'reasoning':e} for r,(m,e) in ROUTES.items()},
        'roles':[], 'capability_violations':[],'acceptance_epochs':[],'repairs':[]}
    stage='architecture'
    try:
        contract=w.role('architect','orchestrator','architecture','orchestrator',{'task':TASK},
            'Act as Architect. Produce a compact complete contract and a few concrete implementation risks. Copy acceptance criteria exactly. Only src/normalize_labels.py may change. No implementation or tools.',CONTRACT_SCHEMA,[])
        stage='implementation'
        implementation=w.role('implementer','implementer','implementation','implementer',{'task':TASK,'contract':contract},
            'Implement normalize_labels normally in the owned Docker workspace. One implementation pass plus useful bounded self-checks is preferred. Use write then check with self-chosen cases. For check, stdin is JSON [[input,expected],...] where expected is a list of strings, or null for expected ValueError. inspect/status only if useful. No raw commands. Report actual completion, changed files, summary, self-check results and uncertainty.',IMPLEMENT_SCHEMA,['inspect','write','check','status'])
        scope=mutation_scope(w); save('mutation-scope',scope)
        require(implementation['outcome']=='completed' and implementation['changed_files']==scope['changed_files'],'Implementer result/scope mismatch')
        candidate=w.workspace('implementer')/'src/normalize_labels.py'
        (OUT/'candidate').mkdir()
        shutil.copyfile(candidate,OUT/'candidate/initial.py')
        initial_hash=sha(candidate)
        stage='test_design'
        tester=w.workspace('tester')
        baseline_hash=sha(w.workspace('orchestrator')/'src/normalize_labels.py')
        require(sha(tester/'src/normalize_labels.py')==baseline_hash,'Candidate present before Tester design')
        design=w.role('test-design','test_engineer','test_design','tester',{'task':TASK,'contract':contract},
            'Independently design 10-24 discriminating cases covering each rule, interacting rules, boundaries, empty/minimal input, quoting/escaping order and invalid-input errors. You receive only the task contract, interface, acceptance and constraints; no candidate, diff, Implementer checks/reasoning or Reviewer opinion. expected is a list of strings, or null meaning ValueError. Pick only useful supported properties. Explain edge-case intents briefly. No tools or implementation. Your artifact will be frozen and executed deterministically by Controller; no Tester execution/narration session.',DESIGN_SCHEMA,[])
        require(sha(tester/'src/normalize_labels.py')==baseline_hash,'Tester baseline changed during design')
        require(len({c['id'] for c in design['cases']})==len(design['cases']),'Duplicate test IDs')
        require(all(c['input'].isascii() and (c['expected'] is None or all(x.isascii() for x in c['expected'])) for c in design['cases']),'Tests exceed ASCII scope')
        (tester/'tests').mkdir(); (tester/'tests/__init__.py').write_text('')
        source=acceptance_source(design); ast.parse(source)
        (tester/'tests/test_acceptance.py').write_text(source,encoding='utf-8')
        shutil.copyfile(tester/'tests/test_acceptance.py',OUT/'independent_tests.py')
        save('test-freeze',{'design_sha256':sha(OUT/'test-design-result.json'),'harness_sha256':sha(tester/'tests/test_acceptance.py'),
            'contract_sha256':sha(OUT/'architect-result.json'),'task_sha256':sha(OUT/'frozen-task.json'),
            'tester_baseline_sha256':baseline_hash,'frozen_at':time.time(),'candidate_visible_during_design':False,
            'test_intent_frozen_before_candidate_exposure':True,
            'test_context_keys':sorted(load(OUT/'test-design-context.json')['bundle'])})
        shutil.copyfile(candidate,tester/'src/normalize_labels.py')
        save('candidate-exposure',{'exposed_at':time.time(),'candidate_sha256':initial_hash,
            'freeze_receipt_sha256':sha(OUT/'test-freeze.json'),'tester_path':str(tester/'src/normalize_labels.py')})
        stage='acceptance_execution'
        execution=controller_execute(w,tester,design,candidate,0)
        assessment['acceptance_epochs'].append(execution)
        for cycle in range(1,limit+1):
            if execution['result']['passed']: break
            classified=classify_failures(execution['result'],design)
            save('failure-classification-'+str(cycle-1),classified)
            require(classified and all(f['classification']=='implementation_defect' for f in classified),
                'Frozen expectation conflicts with contract: explicit test defect; no expectations rewritten')
            stage='repair'
            feedback={'failures':classified,'previous_candidate_sha256':sha(candidate)}
            previous=execution['result']
            repaired=w.role('repair-'+str(cycle),'implementer','fix','implementer',{'task':TASK,'contract':contract,'failure_evidence':feedback},
                'Repair only the demonstrated contract failures. You receive the necessary failing evidence, not the complete independent test suite. Keep mutation scope src/normalize_labels.py, run useful bounded self-checks, and report the repair and uncertainty. check expected is a list, or null for ValueError.',IMPLEMENT_SCHEMA,['write','check','status'])
            scope=mutation_scope(w); save('mutation-scope',scope)
            require(repaired['outcome']=='completed' and repaired['changed_files']==scope['changed_files'],'Repair result/scope mismatch')
            shutil.copyfile(candidate,OUT/('candidate/repair-'+str(cycle)+'.py'))
            shutil.copyfile(candidate,tester/'src/normalize_labels.py')
            stage='acceptance_execution'
            execution=controller_execute(w,tester,design,candidate,cycle)
            assessment['acceptance_epochs'].append(execution)
            old_passed={c['id'] for c in previous['cases'] if c['passed']}
            regressed=[c['id'] for c in execution['result']['cases'] if c['id'] in old_passed and not c['passed']]
            assessment['fix_cycles']=cycle
            assessment['repairs'].append({'cycle':cycle,'failure_evidence':classified,'implementer_result':repaired,
                'regressed_cases':regressed,'candidate_sha256':sha(candidate),'rerun_passed':execution['result']['passed']})
            save('repair-evidence',assessment['repairs'])
            implementation=repaired
        if not execution['result']['passed']:
            save('final-failure-classification',classify_failures(execution['result'],design))
        assessment['tests']={'cases':len(design['cases']),'properties':design['properties'],
            'passed':execution['result']['passed'],'evidence':execution}
        diff=git(w.workspace('implementer'),'diff','--','src/normalize_labels.py')
        (OUT/'final.diff').write_text(diff,encoding='utf-8')
        shutil.copyfile(candidate,OUT/'candidate/final.py')
        stage='review'
        anomalies=sorted({n['anomaly_type'] for r in w.records for meta in [*r.get('gate_observations',[]),
            *r.get('transport_observations',[]),r.get('session_observations',{})] for n in meta.get('anomalies',[])})
        review=w.role('reviewer','reviewer','review','reviewer',{'contract':contract,'task':TASK,'final_diff':diff,
            'implementation_result':implementation,'test_design':design,'acceptance_evidence':assessment['acceptance_epochs'],
            'repair_evidence':assessment['repairs'],'mutation_scope':scope,'relevant_anomalies':anomalies},
            'Review only, concise accept/reject recommendation and specific blockers. Check contract correctness, diff, whether frozen independent tests support acceptance, classification/repair if any, scope, and actual impact of anomalies. No edits or tools. State if you found a correctness concern beyond deterministic evidence; do not restate every artifact.',REVIEW_SCHEMA,[])
        assessment['review']=review
        stage='acceptance'
        own=[t for label in ['implementer']+['repair-'+str(i) for i in range(1,assessment['fix_cycles']+1)]
            for t in load(OUT/(label+'-tools.json')) if t['action']==['check']]
        require(own and any(t['returncode']==0 for t in own),'No successful Implementer verification')
        frozen=load(OUT/'test-freeze.json')
        require(sha(OUT/'test-design-result.json')==frozen['design_sha256'] and sha(OUT/'independent_tests.py')==frozen['harness_sha256'],'Final frozen artifact changed')
        assessment['separation']={'tester_design_before_exposure':frozen['frozen_at']<load(OUT/'candidate-exposure.json')['exposed_at'],
            'candidate_absent_during_design':True,'test_artifact_unchanged':True,
            'candidate_unchanged_during_each_execution':all(e['candidate_sha256_before']==e['candidate_sha256_after'] for e in assessment['acceptance_epochs'])}
        assessment['changed_files']=scope['changed_files']
        assessment['accepted']=bool(assessment['tests']['passed'] and review['recommendation']=='accept' and all(assessment['separation'].values()))
        if assessment['accepted']:
            shutil.copyfile(candidate,w.config.root/'src/normalize_labels.py')
            git(w.config.root,'add','src/normalize_labels.py')
            git(w.config.root,'commit','-m','Accept Stage21 independently tested label parser')
            assessment['accepted_commit']=git(w.config.root,'rev-parse','HEAD')
        assessment['verdict']='PASS' if assessment['accepted'] else 'FAIL_PROJECT_RESULT'
    except BaseException as error:
        message=str(error)
        security=('identity','Unapproved','Unowned','read-only','privileged','Credential','Builtin','Built-in','host process')
        if any(s in message for s in security):
            assessment['verdict']='FAIL_CAPABILITY_BOUNDARY'; assessment['capability_violations'].append(message[:500])
        elif 'test defect' in message: assessment['verdict']='FAIL_TEST_DEFECT'
        elif stage in ('acceptance','acceptance_execution','repair') or 'result/scope' in message: assessment['verdict']='FAIL_PROJECT_RESULT'
        assessment.update(failed_stage=stage,failure_type=type(error).__name__,failure_reason=w.secrets.redact(message)[:1000])
    finally:
        assessment['roles']=w.records
        containment={'production_source_unchanged':w.production_before==production_hashes(),
            'credential_store_unchanged':w.credentials_hashes=={p.name:sha(p) for p in w.store.directory.iterdir() if p.is_file()},
            'stale_owned_containers':len(w.runner.stale_executions()),
            'model_homes_removed':not any((w.config.runtime_root/'model-homes').glob('*')),
            'role_network':'none','host_fallback':False,
            'isolation_preserved':not assessment['capability_violations'] and not any(r.get('host_execution_attempt') for r in w.records)}
        records=[load(p) for p in w.runner.root.glob('executions/*/ownership.json')]
        save('docker-ownership-receipts',records)
        containment['docker_cleanup_confirmed']=all(r.get('cleanup')=='confirmed' and r.get('storage_cleanup')=='confirmed' for r in records)
        if not all(containment[k] for k in ('production_source_unchanged','credential_store_unchanged','model_homes_removed','docker_cleanup_confirmed','isolation_preserved')) or containment['stale_owned_containers']:
            assessment['accepted']=False; assessment['verdict']='FAIL_CAPABILITY_BOUNDARY'
        try:
            remove_owned(w.config.runtime_root,OWNED/'runtime')
            containment['disposable_role_storage_removed']=not w.config.runtime_root.exists()
        except BaseException as cleanup_error:
            assessment['accepted']=False; assessment['verdict']='FAIL_CLEANUP'
            containment['disposable_role_storage_removed']=False
            assessment['cleanup_failure_type']=type(cleanup_error).__name__
        assessment['containment']=containment
        save('production-after',production_hashes())
        save('assessment',assessment)
        for p in OUT.rglob('*'):
            if p.is_file(): w.secrets.reject(p.read_bytes().decode('utf-8',errors='replace'))
        print(json.dumps({'verdict':assessment['verdict'],'accepted':assessment['accepted'],'failed_stage':assessment.get('failed_stage')}),flush=True)
    return 0 if assessment['accepted'] else 1

if __name__=='__main__':
    require(sys.argv[1:] in (['--prepare'],['--run-once']),'Explicit Stage21 entry required')
    OUT.mkdir(parents=True,exist_ok=True)
    if sys.argv[1]=='--prepare': prepare()
    else: raise SystemExit(run())
