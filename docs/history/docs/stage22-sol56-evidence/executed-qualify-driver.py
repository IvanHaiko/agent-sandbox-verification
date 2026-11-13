"""Authorized all-Sol56/medium continuation; Controller-reviewed independent designs."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'validation')]
import stage22_workflow as v
s = v.s
OUT = ROOT/'docs/stage22-sol56-evidence'
OWNED = ROOT/'.test-tmp/stage22-sol56-workflow'
v.OUT, v.OWNED = OUT, OWNED
v.MODEL = v.TESTER_MODEL = 'gpt-5.6-sol'
v.EFFORT = v.TESTER_EFFORT = 'medium'
BASE_TRIAL = v.Trial
INSTRUCTION = ('Independently design 10-24 deterministic ASCII-only cases covering every '
    'contract rule and interactions of quoting, escaping, ordinary and protected whitespace, '
    'deduplication, empty input and whole-input errors. Unicode and non-string inputs are '
    'unspecified: NEVER test them. expected is a string list or null meaning ValueError. '
    'Verify expectations against all rules. No implementation, tools, candidate, or previous designs. '
    'Your structured design is checked and frozen before candidate exposure.')
BUNDLE = {'task':s.TASK,'public_interface':s.TASK['public_interface'],'acceptance_rules':s.CRITERIA}


def structural_gate(design):
    """Only schema/domain/output invariants; deliberately no task implementation/oracle."""
    from jsonschema import Draft202012Validator
    violations = [e.message for e in Draft202012Validator(v.DESIGN_SCHEMA).iter_errors(design)]
    if violations: return violations
    cases = design['cases']
    if len({c['id'] for c in cases}) != len(cases): violations.append('Duplicate case IDs')
    for c in cases:
        expected = c['expected']
        if not c['input'].isascii(): violations.append(c['id']+': non-ASCII input')
        if expected is not None:
            if any(not x or not x.isascii() or any('A'<=ch<='Z' for ch in x) for x in expected):
                violations.append(c['id']+': expected violates nonempty ASCII lowercase output')
            if len(set(expected)) != len(expected): violations.append(c['id']+': expected duplicates')
        if c['input']=='' and expected!=[]: violations.append(c['id']+': empty input must return []')
    return violations


def check_design(design, label):
    violations = structural_gate(design)
    proposed = s.OUT/(label+'-result.json')
    receipt = {'design_sha256':s.sha(proposed),'schema_domain_valid':not violations,
        'candidate_exposed':False,'violations':violations,'oracle_used':False,
        'contract_valid':False,'freezeable':False}
    if not violations:
        pending = s.OUT/(label+'-pending.json')
        review = s.OUT/(label+'-review.json')
        s.atomic_json(pending,{'design':str(proposed),'design_sha256':s.sha(proposed),
            'candidate_exposed':False,'requires':'Controller contract reasoning, without candidate or oracle'})
        print('CONTROLLER_REVIEW_REQUIRED '+str(pending),flush=True)
        deadline=time.monotonic()+240
        while not review.exists() and time.monotonic()<deadline: time.sleep(0.25)
        s.require(review.exists(),'Controller contract review not supplied; no freeze')
        judgment=s.load(review)
        s.require(judgment['design_sha256']==s.sha(proposed),'Review/design hash mismatch')
        s.require(judgment['candidate_exposed'] is False and judgment['oracle_used'] is False,
            'Independent review requirements violated')
        s.require(bool(judgment['reasoning']) and set(judgment['case_ids'])=={c['id'] for c in design['cases']},
            'Controller must examine every proposed case')
        receipt.update(contract_valid=judgment['valid'],freezeable=judgment['valid'],
            violations=judgment['violations'],review_sha256=s.sha(review))
    s.save(label+'-validation',receipt)
    return receipt


class Trial(BASE_TRIAL):
    def __init__(self, trial_id, phase):
        super().__init__(trial_id,phase)
        self.continuation_driver_hash=s.sha(Path(__file__))

    def admission(self):
        if hasattr(self,'continuation_driver_hash'):
            s.require(s.sha(Path(__file__))==self.continuation_driver_hash,'Continuation driver changed')
        super().admission()

    def role(self,label,role,phase,name,bundle,instruction,result_schema,permitted):
        if label!='test-design':
            return super().role(label,role,phase,name,bundle,instruction,result_schema,permitted)
        for attempt in (1,2):
            current=label+'-attempt'+str(attempt)
            design=super().role(current,role,phase,name,bundle,instruction,result_schema,permitted)
            receipt=check_design(design,current)
            if receipt['freezeable']:
                shutil.copyfile(s.OUT/(current+'-result.json'),s.OUT/(label+'-result.json'))
                shutil.copyfile(s.OUT/(current+'-context.json'),s.OUT/(label+'-context.json'))
                s.save('tester-design-selection',{'selected_attempt':attempt,'validation':receipt,
                    'candidate_exposed':False,'frozen_expectations_rewritten':False})
                return design
            bundle={**BUNDLE,'contract_violation':'; '.join(receipt['violations'])[:1800]}
            instruction=INSTRUCTION+' Produce a fresh design addressing the stated violation.'
        raise s.AgentSystemError('Independent Tester failed both pre-exposure checks')


def qualify_one(number):
    w=Trial('qualification-'+str(number),0)
    receipt={'attempt':number,'model':v.MODEL,'reasoning':'medium','candidate_exposed':False,
        'previous_design_visible':False,'valid':False,'freezeable':False,'cases':0,
        'failure_category':None,'roles':w.records}
    try:
        design=BASE_TRIAL.role(w,'qualification-design','test_engineer','test_design','tester',
            BUNDLE,INSTRUCTION,v.DESIGN_SCHEMA,[])
        result=check_design(design,'qualification-design')
        receipt.update(valid=result['contract_valid'],freezeable=result['freezeable'],
            cases=len(design['cases']),design_sha256=result['design_sha256'],validation=result)
    except Exception as error:
        receipt.update(failure_category=next((r['failure_category'] for r in reversed(w.records)
            if r['failure_category']), 'qualification_controller_failure'),
            failure_reason=w.secrets.redact(str(error))[:500])
    finally:
        containment={'production_source_unchanged':w.production_before==s.production_hashes(),
            'credential_store_unchanged':w.credentials_hashes=={p.name:s.sha(p)
                for p in w.store.directory.iterdir() if p.is_file()},
            'stale_owned_containers':len(w.runner.stale_executions()),
            'model_homes_removed':all(r.get('model_home_removed') for r in w.records),
            'host_fallback':False,'no_host_execution_attempt':not any(r.get('host_execution_attempt') for r in w.records)}
        s.remove_owned(s.OWNED,OWNED)
        containment['disposable_storage_removed']=not s.OWNED.exists()
        receipt['containment']=containment
        receipt['cleanup_passed']=containment['stale_owned_containers']==0 and all(containment[k] for k in
            ('production_source_unchanged','credential_store_unchanged','model_homes_removed',
             'no_host_execution_attempt','disposable_storage_removed'))
        if not receipt['cleanup_passed']: receipt['valid']=receipt['freezeable']=False
        s.save('assessment',receipt)
        print(json.dumps({'attempt':number,'valid':receipt['valid'],
            'failure_category':receipt['failure_category'],'cleanup_passed':receipt['cleanup_passed']}),flush=True)
    return receipt


def classify_without_oracle(execution,design):
    return [{**c,'classification':'unresolved_contract_ambiguity',
        'basis':'Frozen disagreement retained for explicit Controller contract reasoning; no oracle.'}
        for c in execution['cases'] if not c['passed']]


def main():
    s.require(sys.argv[1:] in (['--qualify'],['--run-progressive']),'Explicit continuation mode required')
    catalog=s.load(OUT/'catalog.json')
    s.require(catalog['credentials_valid'] and any(m['model']==v.MODEL and 'medium' in m['reasoning']
        for m in catalog['models']),'Requested route unavailable')
    mode=sys.argv[1][2:]
    with (OUT/(mode+'.consumed')).open('x') as f: f.write('Authorized all Sol56 medium continuation\n')
    shutil.copyfile(Path(__file__),OUT/('executed-'+mode+'-driver.py'))
    if mode=='qualify':
        s.atomic_json(OUT/'production-baseline.json',s.production_hashes())
        attempts=[]; streak=0
        for number in range(1,6):
            result=qualify_one(number); attempts.append(result)
            streak=streak+1 if result['valid'] else 0
            state={'attempts':attempts,'consecutive_valid_designs':streak,'qualified':streak>=3}
            s.atomic_json(OUT/'qualification.json',state)
            if streak>=3: return 0
            if result['failure_category'] or not result['cleanup_passed']: return 1
        return 1
    qualification=s.load(OUT/'qualification.json')
    s.require(qualification['qualified'],'Tester not qualified')
    v.Trial=Trial
    s.classify_failures=classify_without_oracle
    trials=[]
    for phase,count in ((1,3),(2,2),(3,2),(4,1)):
        for number in range(1,count+1):
            result=v.run_trial('sol56-p'+str(phase)+'-t'+str(number),phase)
            trials.append(result)
            state={'trials':trials,'completed':False,'model':v.MODEL,'all_role_effort':'medium'}
            s.atomic_json(OUT/'campaign.json',state)
            if not result['workflow_completed'] or not result['accepted']:
                s.atomic_json(OUT/'campaign.json',{**state,'stopped_phase':phase,
                    'stop_reason':'Simpler layer did not pass; no expansion or transport retry'})
                return 1
    s.atomic_json(OUT/'campaign.json',{**state,'completed':True})
    return 0


if __name__=='__main__': raise SystemExit(main())
