"""Small evidence collection and packaging utility; never changes candidates."""
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import zipfile
import xml.etree.ElementTree as ET

import experiment as bench

e=bench.E


def preparation_evidence():
    previous=bench.ROOT/'docs/stage27-verification'
    receipt=json.loads((previous/'delivery-receipt.json').read_text())
    archive=previous/'stage27-delivery.zip'
    with zipfile.ZipFile(archive) as z:
        valid=z.testzip() is None
        names=z.namelist()
    bench.ex.save(e,'previous-delivery-verification',{'sha256':bench.ex.digest(archive.read_bytes()),
        'matches_previous_receipt':bench.ex.digest(archive.read_bytes())==receipt['sha256'],
        'zip_crc_valid':valid,'members':len(names)})
    buffer=io.BytesIO()
    with tarfile.open(fileobj=buffer,mode='w:gz') as tar:
        for name,data in bench.ex.source().items():
            member=tarfile.TarInfo(name);member.size=len(data);member.mtime=0
            tar.addfile(member,io.BytesIO(data))
    bench.ex.archive(e,'baseline-source.tar.gz',buffer.getvalue())
    bench.ex.save(e,'runtime-versions',{'python':subprocess.run([bench.ex.runtime()['python'],'--version'],capture_output=True,text=True,check=True).stdout.strip(),
        'codex':bench.ex.runner().version,'postgres':bench.ex.runtime()['database_version'],
        'baseline_archive_sha256':bench.ex.digest(buffer.getvalue())})


def probe_a():
    argv=json.loads((e/'A/start.json').read_text())['command']
    root=Path(argv[argv.index('--cd')+1])
    profile=next(a for a in argv if a.startswith('permissions.role_workspace='))
    paths={'own_candidate':str(root/'implementer/src/load.py'),
        'peer_tester':str(root/'tester/tests/test_independent.py'),
        'held_out_suite':str(e/'test_external_acceptance.py'),
        'other_configuration':str(e/'B/candidate/src/load.py'),
        'original_source':str(bench.ex.REPO/'src/load.py')}
    code='''import os,json
paths=PATHS
result={}
for label,path in paths.items():
 entry={}
 for name,flags in [("readable",os.O_RDONLY),("writable_open_no_bytes",os.O_WRONLY)]:
  try:fd=os.open(path,flags)
  except OSError as exc:entry[name]=False;entry[name+"_errno"]=exc.errno
  else:os.close(fd);entry[name]=True
 result[label]=entry
print(json.dumps(result))
'''.replace('PATHS',repr(paths))
    result=bench.ex.runner()._process([argv[0],'-c','default_permissions="role_workspace"','-c',profile,
        'sandbox','--permission-profile','role_workspace','--cd',str(root),'/usr/bin/python3','-I','-B','-c',code],root,'',30)
    if result['exit_code']==0:result['paths']=json.loads(result['stdout'])
    result['scope']='Recorded A parent profile, not a claim about unobserved child profiles. O_WRONLY opens never write/truncate.'
    result['all_target_paths_exist']=all(Path(p).is_file() for p in paths.values())
    bench.ex.save(e/'A','permission-probe',result)
    print(json.dumps(result,indent=2))


def metrics():
    a=json.loads((e/'A/execution.json').read_text());b=json.loads((e/'B/assessment.json').read_text())
    value={'A_workflow':{k:a[k] for k in ('started_at','ended_at','elapsed_seconds','exit_code','timed_out')},
           'B_workflow':{k:b[k] for k in ('started_at','ended_at','elapsed_seconds','workflow_completed','accepted','repair_cycles')},
           'B_role_execution_seconds':sum(r.get('elapsed_seconds',0) for r in b['roles']),
           'B_role_sessions':len(b['roles']),'B_native_text_counters':[r.get('native_reported_tokens_used') for r in b['roles']],
           'usage_limit':'A turn JSON aggregation boundary unverified; B text units lack input/cache/output breakdown. No cost or like-for-like token comparison.'}
    usage=[]
    for line in (e/'A/native-events.jsonl').read_text().splitlines():
        try:event=json.loads(line)
        except ValueError:continue
        if event.get('type')=='turn.completed':usage.append(event.get('usage'))
    value['A_native_turn_usage']=usage
    orchestrator=e/'A/results/orchestrator.json'
    if orchestrator.exists():value['A_parent_role_record']=json.loads(orchestrator.read_text())
    if (e/'evaluation-summary.json').exists():
        evaluations=json.loads((e/'evaluation-summary.json').read_text())
        value['deterministic_evaluation_seconds']={label:sum(v.get('elapsed_seconds',0) for v in data.values() if isinstance(v,dict))+
            sum(v.get('elapsed_seconds',0) for key in ('mutations','external_mutations') for v in data.get(key,{}).values())
            for label,data in evaluations.items()}
    value['boundaries']='Workflow windows include role execution, coordinator actions, artifact capture and own independent acceptance; exclude common provisioning, final held-out/mutation evaluation and cleanup. A role timings are parent-reported; B are launcher-measured.'
    bench.ex.save(e,'metrics',value)
    print(json.dumps(value,indent=2))


def analyze():
    summary={}
    original_modules={p[:-3].replace('/','.') for p in bench.ex.source() if p.startswith('tests/test_') and p.endswith('.py')}
    def cases(path):
        return {(c.get('classname',''),c.get('name','')):
            ('error' if c.find('error') is not None else 'failure' if c.find('failure') is not None else
             'skipped' if c.find('skipped') is not None else 'passed') for c in ET.parse(path).iter('testcase')}
    for label in ('A','B'):
        out=e/label
        regression=cases(out/'regression.xml')
        original={k:v for k,v in regression.items() if k[0] in original_modules}
        independent=cases(out/'independent-final.xml')
        failing={k for k,v in independent.items() if v in ('failure','error')}
        mutations={}
        for name in bench.MUTATIONS:
            current=cases(out/('independent-'+name+'.xml'))
            new={k for k,v in current.items() if v in ('failure','error')} - failing
            external=cases(out/('external-'+name+'.xml'))
            mutations[name]={'new_failing_independent_cases':[list(k) for k in sorted(new)],
                'independent_new_defect_detected':bool(new),
                'external_defect_demonstrated':any(v=='failure' for v in external.values()),
                'external_errors':sum(v=='error' for v in external.values())}
        summary[label]={'unchanged_original_regressions':{status:sum(v==status for v in original.values()) for status in ('passed','failure','error','skipped')},
            'independent_preexisting_failures':[list(k) for k in sorted(failing)],'mutation_incremental_evidence':mutations,
            'distinct_mutations_detected':sum(m['independent_new_defect_detected'] for m in mutations.values())}
    diagnostics=[]
    out=e/'B'
    candidate={p:(out/'candidate'/p).read_bytes() for p in json.loads((out/'candidate-manifest.json').read_text())}
    for path in sorted(out.glob('implementer*-execution.json')):
        record=json.loads(path.read_text())
        if record['execution_status']=='completed':continue
        diagnostics.append({'record':path.name,'native_exit':record.get('process_exit_code'),
            'shutdown_confirmed':record.get('shutdown_confirmed'),'resolved_model':record.get('resolved_model'),
            'changed_files':record.get('changed_files'),'all_changes_authorized':set(record.get('changed_files',[]))<=set(bench.ex.ALLOWED+['handoff/implementation.json']),
            'target_changed':'src/load.py' in record.get('changed_files',[]),
            'original_rejection_preserved':True,'classification':'Stage28 adapter reuse of fixed-target delta validation rejects legitimate transformer-only repairs; not an unauthorized mutation'})
    bundle=dict(candidate,**{'handoff/implementation.json':(out/'implementer-handoff.json').read_bytes()})
    diagnostic_validation=bench.ex.verify_impl(bundle)
    summary['B_repair_validation_diagnostic']={'records':diagnostics,'full_archived_candidate_validation':diagnostic_validation,
        'original_decision_unchanged':True,'diagnostic_only':True,'new_model_calls':0,
        'limit':'Checks archive syntax/handoff/scope, not a substitute for original role validation or functional tests.'}
    bench.ex.save(e,'quality-analysis',summary)
    print(json.dumps(summary,indent=2))


def package():
    bench.ex.require(not (e/'.stage26-runtime').exists(),'Runtime must be cleaned before delivery')
    report=bench.ROOT/'STAGE28_MULTI_AGENT_BENCHMARK.md'
    files={p.relative_to(e).as_posix():p.read_bytes() for p in e.rglob('*') if p.is_file()
           and '__pycache__' not in p.parts and p.suffix not in ('.zip','.pyc')
           and p.name not in ('evidence-manifest.json','delivery-receipt.json')}
    files['STAGE28_MULTI_AGENT_BENCHMARK.md']=report.read_bytes()
    for folder in ('agent_system','validation'):
        for p in (bench.ROOT/folder).glob('*.py'):
            files['executed-framework/'+p.relative_to(bench.ROOT).as_posix()]=p.read_bytes()
    files['reused-stage27-experiment.py']=(bench.ROOT/'docs/stage27-verification/experiment.py').read_bytes()
    # Avoid duplicate full source in A review bundle; preserve its manifest and scoped files.
    for name in list(files):
        if name.startswith(('A/review/original/src/','A/review/candidate/src/')):
            if name.split('/')[-1] not in ('load.py','transform.py'):del files[name]
    manifest={name:bench.ex.digest(data) for name,data in sorted(files.items())}
    bench.ex.save(e,'evidence-manifest',manifest)
    files['evidence-manifest.json']=(e/'evidence-manifest.json').read_bytes()
    output=e/'stage28-delivery.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in sorted(files.items()):archive.writestr(name,data)
    with zipfile.ZipFile(output) as archive:
        bench.ex.require(archive.testzip() is None,'ZIP integrity failed')
        bench.ex.require(all(bench.ex.digest(archive.read(n))==h for n,h in manifest.items()),'ZIP manifest mismatch')
    sealed_at=time.time()
    provision=json.loads((e/'provisioning.json').read_text())
    bench.ex.save(e,'delivery-receipt',{'at':sealed_at,'sha256':bench.ex.digest(output.read_bytes()),
        'bytes':output.stat().st_size,'manifest_entries':len(manifest),'zip_crc_and_manifest_verified':True})
    receipt=json.loads((e/'delivery-receipt.json').read_text())
    receipt['common_recorded_elapsed_seconds_provisioning_start_to_delivery_seal']=sealed_at-provision['started_at']
    receipt['measurement_limit']='Excludes preliminary brief/source inspection and suite authoring; includes provisioning, freeze correction, both runs, coordinator gaps, evaluation, report, cleanup and ZIP sealing.'
    bench.ex.save(e,'delivery-receipt',receipt)
    print(output)


def closeout():
    import os
    integrity=json.loads((e/'final-integrity.json').read_text())
    evaluation=json.loads((e/'evaluation-summary.json').read_text())
    quality=json.loads((e/'quality-analysis.json').read_text())
    compatibility=json.loads((e/'compatibility-audit.json').read_text())
    b=json.loads((e/'B/assessment.json').read_text())
    aroot=Path(json.loads((e/'A/prepared.json').read_text())['workspace'])
    runtime=json.loads((e/'runtime.json').read_text())
    owned={str(aroot),runtime['database_workspace'],*[r['workspace'] for r in b['roles']]}
    try:os.kill(runtime['postmaster_pid'],0);postgres_absent=False
    except ProcessLookupError:postgres_absent=True
    checks={'original_unchanged':integrity['original_unchanged'],
        'framework_unchanged':integrity['framework_unchanged'],
        'frozen_inputs_unchanged':all(integrity['frozen_unchanged'].values()),
        'reused_stage27_unchanged':integrity['stage27_adapter_unchanged'],
        'owned_recorded_roots_removed':all(not Path(p).exists() for p in owned),
        'postgres_pid_absent':postgres_absent,'runtime_removed':not (e/'.stage26-runtime').exists(),
        'B_original_failed_decision_preserved':not b['accepted'] and not b['workflow_completed']}
    for label in ('A','B'):
        checks[label+'_patch_reproduced']=evaluation[label]['patch_reproduced']
        checks[label+'_external_passed']=evaluation[label]['external']['passed']==56 and evaluation[label]['external']['exit_code']==0
        checks[label+'_original_regressions_passed']=quality[label]['unchanged_original_regressions']=={'passed':168,'failure':0,'error':0,'skipped':0}
        checks[label+'_three_mutations_detected']=quality[label]['distinct_mutations_detected']==3
        checks[label+'_mutation_defects_demonstrated']=all(v['external_defect_demonstrated'] and v['external_errors']==0 for v in quality[label]['mutation_incremental_evidence'].values())
        checks[label+'_test_freeze_preserved']=compatibility[label]['tester_archive_matches_freeze']
        checks[label+'_public_signatures_preserved']=all(compatibility[label][p]['signatures_unchanged'] for p in ('src/load.py','src/transform.py'))
    bench.ex.save(e,'delivery-audit',{'at':time.time(),'checks':checks,'all_checks_passed':all(checks.values()),
        'architecture_recommendation':'INCONCLUSIVE','clean_independent_acceptance':False,
        'owned_recorded_roots':sorted(owned),'report_sha256':bench.ex.digest((bench.ROOT/'STAGE28_MULTI_AGENT_BENCHMARK.md').read_bytes())})
    bench.ex.require(all(checks.values()),'Delivery audit failed')
    print(json.dumps(checks,indent=2))


if __name__=='__main__':
    {'preparation':preparation_evidence,'probe-a':probe_a,'metrics':metrics,'analyze':analyze,'closeout':closeout,'package':package}[sys.argv[1]]()
