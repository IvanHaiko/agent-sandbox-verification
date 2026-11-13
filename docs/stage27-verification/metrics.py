"""Summarize preserved observations without converting counters to billing costs."""
import ast
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import experiment as ex

e=ex.E
summary=json.loads((e/'evaluation-summary.json').read_text())
metrics={'environment_setup':json.loads((e/'provisioning.json').read_text()),
         'configurations':{},'counter_warning':'A JSON usage and B native text counters have different scopes and fields; no cost or total-token ranking.'}
for label in ('A','B'):
    out=e/label
    counts={}
    for case in ET.fromstring((out/'regression.xml').read_bytes()).iter('testcase'):
        name=case.attrib['classname']
        bucket='external' if 'stage27_evaluation' in name else 'candidate_tests' if 'test_migration_sql' in name else 'existing_tests'
        row=counts.setdefault(bucket,{'tests':0,'failed':0,'errors':0,'skipped':0})
        row['tests']+=1
        for key,tag in [('failed','failure'),('errors','error'),('skipped','skipped')]:
            row[key]+=case.find(tag) is not None
    designpath=out/'frozen/test-design.json' if label=='A' else out/'frozen-test-design.json'
    design=json.loads(designpath.read_text())
    candidates={p:(out/'candidate'/p).read_bytes() for p in json.loads((out/'candidate-manifest.json').read_text())}
    row={'evaluation':summary[label],'regression_groups':counts,
         'requirements_covered':sorted({c['requirement'] for c in design['cases']}),
         'independent_cases_in_manifest':len(design['cases']),
         'candidate_lines':{p:len(b.decode().splitlines()) for p,b in candidates.items()},
         'candidate_functions':{p:[n.name for n in ast.parse(b.decode()).body if isinstance(n,ast.FunctionDef)] for p,b in candidates.items()},
         'patch_sha256':ex.digest((out/'implementation.patch').read_bytes()),
         'development_checks':[]}
    for path in sorted(out.glob('implementer-check-*.json')):
        check=json.loads(path.read_text())
        row['development_checks'].append({'file':path.name,'check':check['check'],'exit_code':check['exit_code'],
            'final_candidate_hashes_match':all(check['source_hashes'].get(p)==ex.digest(b) for p,b in candidates.items())})
    if label=='A':
        execution=json.loads((out/'execution.json').read_text())
        orchestration=json.loads((out/'results/orchestrator.json').read_text())
        row['recorded_execution_seconds']=execution['elapsed_seconds']
        row['roles_parent_reported']=orchestration['roles']
        row['native_json_usage']=[json.loads(line)['usage'] for line in (out/'native-events.jsonl').read_text().splitlines()
                                  if json.loads(line).get('type')=='turn.completed']
        row['role_sessions']=4
        row['usage_scope']='CLI turn.completed usage; separate child usage not exposed; aggregation scope unverified'
        row['role_seconds_sum_parent_reported']=sum(r['duration_seconds'] for r in orchestration['roles'].values())
        row['acceptance_setup_attempts']=[{'file':p.name,**{k:json.loads(p.read_text())[k] for k in ('check','exit_code')}}
                                        for p in sorted(out.glob('orchestrator-acceptance-*.json'))]
    else:
        assessment=json.loads((out/'assessment.json').read_text())
        row['recorded_original_execution_seconds']=assessment['elapsed_seconds']
        row['original_workflow_completed']=assessment['workflow_completed']
        row['roles']=[]
        for role in ('implementer','independent_tester','reviewer'):
            record=json.loads((out/(role+'-execution.json')).read_text())
            row['roles'].append({key:record.get(key) for key in ('role','resolved_model','reasoning','elapsed_seconds',
                'native_reported_tokens_used','execution_status','sandbox_preflight_passed','mutation_scope_valid','failure_closeout')})
        row['role_sessions']=3
        row['native_reported_counter_sum']=sum(r['native_reported_tokens_used'] or 0 for r in row['roles'])
        row['review_closeout_seconds']=row['roles'][-1]['elapsed_seconds']
        row['usage_scope']='Sum of native tokens used text counters for three role invocations; no input/output/cache breakdown; includes closeout reviewer'
    row['shared_evaluation_and_controls_seconds']=sum(summary[label][key]['elapsed_seconds'] for key in ('external','regression','independent'))+sum(x['elapsed_seconds'] for x in summary[label]['mutations'].values())+sum(x['elapsed_seconds'] for x in summary[label]['external_mutations'].values())
    metrics['configurations'][label]=row
ex.save(e,'metrics',metrics)
print(json.dumps(metrics,indent=2))
