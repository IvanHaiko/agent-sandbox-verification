"""Audit archived observations and package this single benchmark's deliverables."""
import hashlib
import json
from pathlib import Path
import time
import zipfile

e=Path(__file__).resolve().parent
root=e.parents[1]
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

checks={}
frozen=read(e/'freeze.json')
checks['frozen_inputs_unchanged']=all(sha(e/p)==h for p,h in frozen['sha256'].items())
checks['original_checkout_unchanged']=read(e/'original-before.json')==read(e/'original-after.json')
checks['framework_unchanged']=read(e/'final-integrity.json')['framework_unchanged']
checks['owned_resources_removed']=all(read(e/'host-cleanup-audit.json')['owned_paths_absent'].values()) and read(e/'host-cleanup-audit.json')['recorded_postmaster_pid_absent']
metrics=read(e/'metrics.json')
for label in ('A','B'):
    out=e/label
    checks[label+'_candidate_hashes']=all(sha(out/'candidate'/p)==h for p,h in read(out/'candidate-manifest.json').items())
    checks[label+'_patch_reproduced']=read(out/'evaluation-summary.json')['patch_reproduced']
    checks[label+'_external_passed']=read(out/'evaluation-summary.json')['external']==metrics['configurations'][label]['evaluation']['external'] and read(out/'evaluation-summary.json')['external']['passed']==24
    checks[label+'_unchanged_regressions_passed']=metrics['configurations'][label]['regression_groups']['existing_tests']=={'tests':168,'failed':0,'errors':0,'skipped':0}
    checks[label+'_final_development_checks']=all(any(c['check']==name and c['exit_code']==0 and c['final_candidate_hashes_match'] for c in metrics['configurations'][label]['development_checks']) for name in ('unit','integration','lint'))
    checks[label+'_both_independent_mutations_detected']=all(r['failed']>0 and r['errors']==0 and r['skipped']==0 for r in read(out/'evaluation-summary.json')['mutations'].values())
    status=read(out/'candidate-status.json')['status']
    names={line[3:] for line in status.splitlines()}
    checks[label+'_candidate_modification_scope']=names=={'src/migrations.py','src/sql_statements.py','tests/test_migration_sql.py','handoff/implementation.json'}
afreeze=read(e/'A/results/orchestrator.json')['freeze']
checks['A_independent_artifacts_frozen']=all(sha(e/'A/frozen'/name)==v['sha256'] and (e/'A/frozen'/name).read_bytes()==(e/'A/tester/tests'/name).read_bytes() for name,v in afreeze['files'].items())
checks['A_freeze_before_implementation']=afreeze['time']<read(e/'A/results/orchestrator.json')['roles']['implementer']['started_at']
bfreeze=read(e/'B/test-freeze.json')
checks['B_independent_artifacts_frozen']=sha(e/'B/frozen-test-design.json')==bfreeze['design_sha256'] and sha(e/'B/frozen-acceptance.py')==bfreeze['harness_sha256'] and sha(e/'B/frozen-task.json')==bfreeze['task_sha256']
checks['B_original_failed_decision_preserved']=read(e/'B/controller-decision.json')=={'accepted':False,'workflow_completed':False} and read(e/'B/assessment.json')['failure']['reason']=='Linked workspace entry'
checks['B_scheduled_review_read_only']=read(e/'B/reviewer-execution.json')['read_only'] and read(e/'B/reviewer-execution.json')['mutation_scope_valid'] and read(e/'B/reviewer-execution.json')['execution_status']=='completed'
checks['both_reviewers_accept_inspected_code']=read(e/'A/results/reviewer-result.json')['recommendation']=='accept' and read(e/'B/reviewer-result.json')['recommendation']=='accept'
assert all(checks.values()),checks
report=root/'STAGE27_MULTI_AGENT_BENCHMARK.md'
audit={'at':time.time(),'checks':checks,'architecture_recommendation':'INCONCLUSIVE',
       'report_sha256':sha(report),'measurement_window_seconds_provisioning_start_to_seal':time.time()-read(e/'provisioning.json')['started_at'],
       'measurement_limit':'Excludes preliminary source/brief inspection and contract/suite authoring; includes coordinator gaps, failure closeout, evaluation and report writing; package compression follows.'}
(e/'delivery-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
excluded={'evidence-manifest.json','stage27-delivery.zip','delivery-receipt.json'}
files=[p for p in e.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name not in excluded]
manifest={p.relative_to(root).as_posix():sha(p) for p in sorted(files)}
manifest[report.name]=sha(report)
(e/'evidence-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
archive=e/'stage27-delivery.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as bundle:
    for name in sorted(manifest):bundle.write(root/name,name)
    bundle.write(e/'evidence-manifest.json','docs/stage27-verification/evidence-manifest.json')
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert all(hashlib.sha256(bundle.read(name)).hexdigest()==h for name,h in manifest.items())
receipt={'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,
         'manifest_entries':len(manifest),'zip_integrity_verified':True,'all_checks_passed':True}
(e/'delivery-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt,indent=2))
