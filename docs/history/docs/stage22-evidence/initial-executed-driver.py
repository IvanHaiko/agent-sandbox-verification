"""Sequential Stage22 trials using existing admitted transport/Docker selectors."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'validation')]
import stage21_workflow as s
from agent_system.artifact_execution import ArtifactImplementerSession, implementation_handoff
from agent_system.runtime_observability import safe_failure

OUT = ROOT / 'docs/stage22-evidence'
OWNED = ROOT / '.test-tmp/stage22-workflow'
MODEL = 'gpt-5.6-luna'
EFFORT = 'low'


def prepare():
    """Reuse source-bound signed admission, rebound only to a fresh trial project."""
    import yaml
    s.require(not s.OWNED.exists(), 'Trial storage already exists')
    old=s.load(OUT/'fresh-admission.json')
    old_runner=s.ToolDockerRunner(s.Configuration.load(Path(old['project'])))
    s.require(old_runner.preflight()==old['binding'],'Current admission binding changed')
    old_runner.require_transport_admission()
    old_store=old_runner._store()
    validation=old_store.verify('validation'); transport=old_store.verify('stage18c-transport')
    project=s.OWNED/'project'; project.mkdir(parents=True)
    shutil.copytree(ROOT/'.agent_system',project/'.agent_system')
    conf=yaml.safe_load((Path(old['project'])/'.agent_system/project.yaml').read_text())
    conf['runtime']={'version':2,'root':str(s.OWNED/'runtime')}
    (project/'.agent_system/project.yaml').write_text(yaml.safe_dump(conf))
    (project/'src').mkdir()
    (project/s.TASK['file']).write_text('def normalize_labels(value: str) -> list[str]:\n    raise NotImplementedError\n')
    s.atomic_json(project/'TASK.json',s.TASK)
    (project/'.gitignore').write_text('__pycache__/\n*.pyc\n')
    s.git(project,'init','--initial-branch=main'); s.git(project,'config','user.name','Stage22 Controller')
    s.git(project,'config','user.email','stage22@example.invalid'); s.git(project,'add','.')
    s.git(project,'commit','-m','Freeze Stage22 task and baseline')
    config=s.Configuration.load(project); runner=s.ToolDockerRunner(config); binding=runner.preflight()
    s.require({k:v for k,v in binding.items() if k!='project'}==
        {k:v for k,v in old['binding'].items() if k!='project'},'Containment binding changed')
    new_store=runner._store(); new_store.directory.mkdir(parents=True,exist_ok=True)
    for cap in validation['capabilities'].values():
        for name,expected in cap.get('evidence',[]):
            src=old_store.directory/name; dst=new_store.directory/name
            s.require(s.sha(src)==expected,'Inherited evidence changed')
            dst.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,dst)
    new_store.issue('validation',validation)
    shutil.copyfile(old_store.directory/'stage18c-proof.json',new_store.directory/'stage18c-proof.json')
    new_store.issue('stage18c-transport',transport); runner.require_transport_admission()
    base=s.git(project,'rev-parse','HEAD'); manifest={'task_id':s.TASK_ID,'base_commit':base,'worktrees':{}}
    for name in ('orchestrator','implementer','tester','reviewer'):
        workspace=config.worktrees_dir/s.TASK_ID/name
        s.IsolatedCheckout.create(project,workspace,base,config.runs_dir/s.TASK_ID/'controller'/name)
        manifest['worktrees'][name]={'path':str(workspace),'kind':'isolated_checkout'}
    s.atomic_json(config.runs_dir/s.TASK_ID/'worktrees.json',manifest)
    s.save('prepared',{'project':str(project),'binding':binding,'manifest':manifest,
        'inherited_admission':True,'fresh_adversarial_probes':False,'source':str(old_store.directory)})
    s.save('frozen-task',s.TASK)


class ArtifactSession(ArtifactImplementerSession, s.UsageSession):
    pass


class Trial(s.Workflow):
    def __init__(self, trial_id, phase):
        self.trial_id, self.phase = trial_id, phase
        s.OUT = OUT / trial_id
        s.OWNED = OWNED / trial_id
        s.OUT.mkdir(parents=True)
        prepare()
        super().__init__()
        self.stage22_driver_hash = s.sha(Path(__file__))
        self.baseline = {'hashes': s.file_map(self.workspace('implementer')),
            'source': (self.workspace('implementer') / s.TASK['file']).read_text()}

    def admission(self):
        s.require(s.sha(Path(__file__)) == self.stage22_driver_hash, 'Stage22 driver changed')
        s.require(self.production_before == s.production_hashes(), 'Production source changed during trial')
        super().admission()

    def role(self, label, role, phase, name, bundle, instruction, result_schema, permitted):
        self.admission()
        workspace = self.workspace(name)
        before = s.file_map(workspace)
        policy = s.ExecutionPolicy(s.InvocationBinding(self.trial_id+'-'+label, role,
            s.TASK_ID, 1, MODEL, EFFORT), phase,
            hashlib.sha256(str(workspace.resolve()).encode()).hexdigest(),
            time.monotonic()+180, max_requests=2 if permitted else 1,
            max_tool_calls=1, max_tool_seconds=20, output_bytes=65536)
        approvals = s.ApprovalStore(self.config.runtime_root/'workflow-approvals'/label,
            {'binding': self.prepared['binding'], 'driver': self.stage22_driver_hash,
             'context': hashlib.sha256(json.dumps(bundle,sort_keys=True).encode()).hexdigest()})
        approvals.issue('no-credits/'+policy.binding.execution_id,
            {'execution_id':policy.binding.execution_id, 'client_id':self.client_id,
             'credits_fallback_disabled':True, 'operator':'Existing human OFF preference retained',
             'attested_at':self.confirmed_at})
        approvals.issue('live-smoke/'+policy.binding.execution_id,
            {'authorized':True, **policy.identity(), 'model':MODEL,'reasoning':EFFORT,'route':s.UPSTREAM})
        actions = s.Actions(policy, permitted)
        bridge = s.ActionBridge(self.runner,workspace,self.task,policy,self.secrets,actions=actions)
        gate = s.ActionGate(policy,self.secrets,actions=actions)
        upstream = s.PlanUpstream(self.store,policy,approvals,self.admission,self.runner.cancel_event)
        prompt = instruction+'\nImmutable input:\n'+json.dumps(bundle)
        if not permitted:
            prompt += '\nReturn ONLY JSON matching: '+json.dumps(result_schema)
        self.secrets.reject(prompt)
        context={'identity':policy.identity(),'model':MODEL,'reasoning':EFFORT,'bundle':bundle,
            'instruction':instruction,'result_schema':result_schema,'previous_conversation_visible':False}
        s.save(label+'-context',context)
        context_hash=s.sha(s.OUT/(label+'-context.json'))
        record={'label':label,**policy.identity(),'model':MODEL,'reasoning':EFFORT,
            'completed':False,'execution_status':'unrecoverable','requests':0,'tool_calls':0,
            'candidate_sha256':None,'frozen_tester_sha256':None,'failure_category':None}
        self.records.append(record)
        exe=self.prepared['binding']['stage18c']['codex']
        home=self.config.runtime_root/'model-homes'/label
        session=None; result=None; started=time.monotonic()
        print(self.trial_id+': starting '+label+' '+MODEL+'/'+EFFORT,flush=True)
        try:
            with s.host_trap(record,exe['path']):
                with s.LocalModelRelay(gate,upstream) as relay:
                    cls=ArtifactSession if permitted else s.UsageSession
                    session=cls(Path(exe['path']),exe['sha256'],home,relay,bridge,policy,
                        diagnostic_directory=s.OUT/'diagnostics'/label)
                    try:
                        with session:
                            if permitted: session.run_until_written(prompt)
                            else: result=session.run(prompt,result_schema)
                    finally:
                        private=s.SecretFilter([relay.child_channel()])
                        for p in home.rglob('*'):
                            if p.is_file(): private.reject(p.read_bytes().decode('utf-8',errors='replace'))
            record['completed']=True
            record['execution_status']='completed'
        except Exception as error:
            if session and session.failure_receipt is None: session._preserve_failure(error)
            receipt=getattr(session,'failure_receipt',None)
            record['failure_category']=(receipt or safe_failure(error))['failure_category'] if receipt else safe_failure(error)['category']
            if not permitted: raise
        finally:
            bridge.close()
            if session: session.close()
            record.update(requests=gate.requests,tool_calls=bridge.calls,
                seconds=round(time.monotonic()-started,2),usage=getattr(session,'usage',None),
                process_exited=bool(session and session.process and session.process.poll() is not None),
                gate_observations=gate.response_metadata_history,
                transport_observations=upstream.response_metadata_history,
                session_observations=getattr(session,'observation_metadata',{}),
                failure_receipt=getattr(session,'failure_receipt',None))
            record['controller_host_process_names']=sorted(record.get('controller_host_process_names',[]))
            s.save(label+'-tools',bridge.evidence)
            s.remove_owned(home,self.config.runtime_root)
            record['model_home_removed']=not home.exists()
            s.save('role-counts',self.records)
        s.require(s.sha(s.OUT/(label+'-context.json'))==context_hash,'Immutable role input changed')
        if permitted:
            def interface(data):
                self.secrets.reject(data.decode('utf-8'))
                observed={}
                with s.host_trap(observed,exe['path']):
                    cp=self.runner.run_tool(['python','-c',s.CHECK],workspace,self.task,
                        'implementer','implementation',True,'[]',20)
                s.save('controller-interface',{'returncode':cp.returncode,'stdout':cp.stdout,
                    'stderr':cp.stderr,'model_requests':0})
                s.require(cp.returncode==0,'Controller interface check failed')
                return s.strict_json(cp.stdout.strip())
            result=implementation_handoff(workspace,self.baseline,s.TASK['file'],
                s.OUT/'candidate/unaccepted.py',successful_write_paths=bridge.successful_write_paths,
                failure_category=record['failure_category'],
                security_violation=bool(record.get('host_execution_attempt') or bridge.failure_receipt
                    or any(m.get('secret_checked') is False for m in upstream.response_metadata_history)),
                shutdown_confirmed=record['process_exited'],interface_check=interface,
                model_handoff_received=session.handoff_status=='completed')
            record['execution_status']=result['execution_status']
            record['candidate_sha256']=result['candidate_hashes'][s.TASK['file']]
            record['termination']='controller_after_successful_write' if record['completed'] else 'abnormal'
        else:
            s.require(s.file_map(workspace)==before,'Semantic role mutated workspace')
        s.save(label+'-result',result); s.save('role-counts',self.records)
        print(self.trial_id+': finished '+label+' '+record['execution_status']+
            ', requests='+str(gate.requests)+', tools='+str(bridge.calls),flush=True)
        return result


def run_trial(trial_id,phase):
    w=Trial(trial_id,phase)
    assessment={'trial_id':trial_id,'phase':phase,'task_id':s.TASK_ID,'accepted':False,
        'workflow_completed':False,'failure_category':None,'roles':w.records,
        'tester_reached':False,'acceptance_reached':False,'review':None,
        'candidate_sha256':None,'frozen_tester_sha256':None}
    started=time.monotonic(); stage='implementation'
    try:
        contract=s.TASK
        if phase>=3:
            stage='architecture'
            proposed=w.role('architect','orchestrator','architecture','orchestrator',{'task':s.TASK},
                'Produce a compact contract refinement. Copy interface, all acceptance criteria and sole allowed mutation scope exactly. Add only useful risks; no implementation or tools.',s.CONTRACT_SCHEMA,[])
            # Architect cannot redefine frozen task semantics.
            s.require(proposed['public_interface']==s.TASK['public_interface'] and
                proposed['acceptance_criteria']==s.CRITERIA and
                proposed['allowed_mutation_scope']==[s.TASK['file']], 'Architect contract mismatch')
            contract={**s.TASK,'risks':proposed['risks']}
            s.save('normalized-contract',contract)
        stage='implementation'
        implementation=w.role('implementer','implementer','implementation','implementer',
            {'task':s.TASK,'contract':contract},
            'Implement the complete normalize_labels contract. Use exactly ONE Controller write action with argv=["write","src/normalize_labels.py"] and stdin containing complete Python source. Set read_only=false. No inspect, check, raw commands or other actions. The Controller ends execution after successful write, then checks scope/interface and independently tests it. Final prose is unnecessary.',None,['write'])
        candidate=w.workspace('implementer')/s.TASK['file']
        assessment['implementation']=implementation
        assessment['candidate_sha256']=s.sha(candidate)
        tester=w.workspace('tester'); baseline_hash=hashlib.sha256(w.baseline['source'].encode()).hexdigest()
        s.require(s.sha(tester/s.TASK['file'])==baseline_hash,'Candidate visible before test design')
        stage='test_design'; assessment['tester_reached']=True
        design=w.role('test-design','test_engineer','test_design','tester',
            {'task':s.TASK,'public_interface':s.TASK['public_interface'],'acceptance_rules':s.CRITERIA},
            'Independently design 10-24 deterministic cases covering rules, interacting quoting/escaping/ordinary versus protected whitespace, deduplication, empty input and whole-input errors. expected is a string list or null meaning ValueError. No implementation, tools or candidate. Your structured design is frozen before exposure and Controller-executed; there is no second Tester session.',s.DESIGN_SCHEMA,[])
        s.require(s.sha(tester/s.TASK['file'])==baseline_hash,'Test baseline changed')
        s.require(len({c['id'] for c in design['cases']})==len(design['cases']),'Duplicate test IDs')
        s.require(all(c['input'].isascii() and (c['expected'] is None or all(x.isascii() for x in c['expected'])) for c in design['cases']),'Test exceeds supported scope')
        (tester/'tests').mkdir(); (tester/'tests/__init__.py').write_text('')
        harness=s.acceptance_source(design); ast.parse(harness)
        (tester/'tests/test_acceptance.py').write_text(harness,encoding='utf-8')
        shutil.copyfile(tester/'tests/test_acceptance.py',s.OUT/'independent_tests.py')
        s.save('test-freeze',{'design_sha256':s.sha(s.OUT/'test-design-result.json'),
            'harness_sha256':s.sha(tester/'tests/test_acceptance.py'),
            'task_sha256':s.sha(s.OUT/'frozen-task.json'),'tester_baseline_sha256':baseline_hash,
            'frozen_at':time.time(),'candidate_visible_during_design':False,
            'test_context_keys':sorted(s.load(s.OUT/'test-design-context.json')['bundle'])})
        assessment['frozen_tester_sha256']=s.sha(s.OUT/'test-design-result.json')
        w.records[-1]['frozen_tester_sha256']=assessment['frozen_tester_sha256']
        shutil.copyfile(candidate,tester/s.TASK['file'])
        s.save('candidate-exposure',{'exposed_at':time.time(),'candidate_sha256':s.sha(candidate),
            'freeze_receipt_sha256':s.sha(s.OUT/'test-freeze.json')})
        stage='acceptance'; assessment['acceptance_reached']=True
        execution=s.controller_execute(w,tester,design,candidate,0)
        assessment['acceptance']=execution
        if not execution['result']['passed']:
            assessment['failures']=s.classify_failures(execution['result'],design)
        if phase>=2:
            stage='review'
            assessment['review']=w.role('reviewer','reviewer','review','reviewer',
                {'task':s.TASK,'final_diff':implementation['diff_summary'],
                 'independent_test_evidence':execution['result'],'implementation_handoff':implementation},
                'Review only the supplied contract, diff and Controller evidence. Recommend accept, reject or request-fix. Identify concrete in-scope defects or missing evidence; no tools or implementation history.',s.REVIEW_SCHEMA,[])
        assessment['workflow_completed']=True
        assessment['accepted']=execution['result']['passed'] and (phase==1 or assessment['review']['recommendation']=='accept')
    except Exception as error:
        assessment.update(failed_stage=stage,failure_type=type(error).__name__,
            failure_category=next((r['failure_category'] for r in reversed(w.records) if r['failure_category']),safe_failure(error)['category']),
            failure_reason=w.secrets.redact(str(error))[:500])
    finally:
        receipts=[s.load(p) for p in w.runner.root.glob('executions/*/ownership.json')]
        s.save('docker-ownership-receipts',receipts)
        containment={'production_source_unchanged_during_trial':w.production_before==s.production_hashes(),
            'credential_store_unchanged':w.credentials_hashes=={p.name:s.sha(p) for p in w.store.directory.iterdir() if p.is_file()},
            'stale_owned_containers':len(w.runner.stale_executions()),
            'docker_cleanup_confirmed':bool(receipts) and all(r.get('cleanup')=='confirmed' and r.get('storage_cleanup')=='confirmed' for r in receipts),
            'model_homes_removed':all(r.get('model_home_removed') for r in w.records),
            'role_network':'none','host_fallback':False,
            'no_host_execution_attempt':not any(r.get('host_execution_attempt') for r in w.records)}
        s.save('role-counts',w.records)
        try:
            s.remove_owned(s.OWNED,OWNED)
            containment['disposable_storage_removed']=not s.OWNED.exists()
        except Exception as error:
            containment['disposable_storage_removed']=False
            assessment['cleanup_failure']=type(error).__name__
        cleanup_ok=containment['stale_owned_containers']==0 and all(containment[k] for k in
            ('production_source_unchanged_during_trial','credential_store_unchanged','docker_cleanup_confirmed',
             'model_homes_removed','no_host_execution_attempt','disposable_storage_removed'))
        assessment['cleanup_result']='passed' if cleanup_ok else 'failed'
        assessment['containment']=containment
        if not cleanup_ok:
            assessment['accepted']=False; assessment['workflow_completed']=False
            assessment['failure_category']='cleanup_or_containment_failure'
        assessment['elapsed_seconds']=round(time.monotonic()-started,2)
        # Acceptance promotion occurs only after independent tests, optional review and cleanup.
        if assessment['accepted']:
            (s.OUT/'accepted').mkdir()
            shutil.copyfile(s.OUT/'candidate/unaccepted.py',s.OUT/'accepted/normalize_labels.py')
            s.save('acceptance-receipt',{'accepted':True,'candidate_sha256':assessment['candidate_sha256'],
                'frozen_tester_sha256':assessment['frozen_tester_sha256'],'cleanup_verified':True})
        s.save('assessment',assessment)
        for p in s.OUT.rglob('*'):
            if p.is_file(): w.secrets.reject(p.read_bytes().decode('utf-8',errors='replace'))
        print(json.dumps({k:assessment[k] for k in ('trial_id','workflow_completed','accepted','failure_category','cleanup_result')}),flush=True)
    return assessment


def main():
    s.require(sys.argv[1:]==['--run-progressive'],'Explicit progressive Stage22 entry required')
    catalog=s.load(OUT/'catalog.json')
    s.require(catalog['credentials_valid'] and any(m['model']==MODEL and EFFORT in m['reasoning'] for m in catalog['models']), 'Cheap route unavailable')
    with (OUT/'progressive-run.consumed').open('x') as f:
        f.write('One authorized sequential Stage22 validation campaign.\n')
    shutil.copyfile(Path(__file__),OUT/'executed-driver.py')
    s.atomic_json(OUT/'production-baseline.json',s.production_hashes())
    trials=[]
    for phase,count in ((1,3),(2,2),(3,2),(4,1)):
        for number in range(1,count+1):
            result=run_trial('p'+str(phase)+'-t'+str(number),phase)
            trials.append(result)
            s.atomic_json(OUT/'campaign.json',{'trials':trials,'completed':False})
            # Small sample evidence must actually pass before expanding the chain.
            if not result['workflow_completed'] or not result['accepted']:
                s.atomic_json(OUT/'campaign.json',{'trials':trials,'completed':False,'stopped_phase':phase,
                    'stop_reason':'Simpler layer did not pass; no role expansion or automatic retry'})
                return 1
    s.atomic_json(OUT/'campaign.json',{'trials':trials,'completed':True})
    return 0


if __name__=='__main__': raise SystemExit(main())
