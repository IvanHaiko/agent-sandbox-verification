"""Check Stage 29 evidence, then package selected small artifacts with hashes."""
import ast
import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
E=Path(__file__).resolve().parent

def sha(data): return hashlib.sha256(data).hexdigest()
def read(name): return json.loads((E/(name+'.json')).read_text(encoding='utf-8'))
def write(name,value): (E/(name+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')

assert read('workspace-integrity')['unchanged'], 'Pre-existing workspace drift'
assert read('original-integrity')['unchanged'], 'Original checkout drift'
assert read('cleanup')['all_removed'], 'Owned workspace remains'
assert all(x['removed'] for x in read('cleanup')['stage29_scratch'])
assert all(x['digest_matches'] and x['crc_error'] is None for x in read('previous-archives-audit'))
assert read('c-acceptance')['result']=={'passed':True,'cases':10,'failures':[]}
assert read('c-acceptance')['inputs_unchanged']
assert read('c-reviewer-result')['recommendation']=='accept'
assert all(read('c-'+role+'-execution')['execution_status']=='completed' for role in ('tester','implementer','reviewer'))
assert read('c-review-integrity')['inputs_unchanged'] and read('c-review-integrity')['freeze_unchanged']
freeze=read('c-freeze')
assert sha((E/'c-frozen-design.json').read_bytes())==freeze['design_sha256']
assert sha((E/'c-frozen-acceptance.py').read_bytes())==freeze['harness_sha256']
assert sha((E/'c-contract.md').read_bytes())==freeze['contract_sha256']
assert sha((E/'c-candidate.py.txt').read_bytes())==read('c-review-integrity')['candidate_sha256']
assert sha((E/'c-candidate.py.txt').read_bytes())==read('c-implementer-execution')['artifact_hashes']['src/candidate.py']
assert read('c-implementer-start')['at']>=read('c-freeze')['frozen_at']
for n in ('custom_configured_tester','custom_configured_reviewer'):
    assert all(not x['allowed'] for x in read('experiment-a')[n]['observations'].values())
assert read('experiment-a-native-explicit')['observations']['review-write']['allowed'] is False
native=read('native-agent-probe')
assert all(x['success'] for x in native['reads']) and native['review_target_write_probe']['open_success']
assert native['review_target_write_probe']['hash_unchanged']
assert not read('b-oracle')['assertion_passed']
assert all(x['receipt']['execution_status']=='unrecoverable' and x['controller_cleanup_passed']
           and not x['rejected_candidate_preserved'] for x in read('experiment-b') if 'receipt' in x)
for p in E.glob('*.py'): ast.parse(p.read_text(encoding='utf-8'))
junit=ET.parse(E/'framework-regression.xml').getroot()
cases=list(junit.iter('testcase'))
assert len(cases)==43 and not list(junit.iter('failure')) and not list(junit.iter('error')) and not list(junit.iter('skipped'))
inventory=read('source-inventory')
for entry in inventory:
    assert sha((ROOT/entry['path']).read_bytes())==entry['sha256'], entry['path']
before=read('workspace-before')
summary={'date_local':'2026-10-09','timezone':'Europe/Berlin','decision':'SIMPLIFY',
    'active_source_unchanged':True,'preexisting_readable_workspace_files_unchanged':True,
    'workspace_entries_recorded':len(before),'historical_unreadable_entries':sum(v.startswith('UNREADABLE:') for v in before.values()),
    'original_checkout_unchanged':True,'owned_resources_cleaned':True,'previous_archive_digests_and_crcs_valid':True,
    'framework_regression':{'passed':43,'failed':0,'errors':0,'skipped':0},
    'minimal_acceptance':{'passed':10,'failed':0},'review_recommendation':'accept',
    'strict_cli_role_calls':3,'strict_cli_role_retries':0,'native_context_canary_children':1,
    'native_default_child_private_reads_allowed':True,'native_default_child_review_write_open_allowed':True,
    'narrow_native_profiles_deny_private_reads_and_review_writes':True,
    'base_controller_rejected_bytes_lost':True,'authorized_secondary_only_repair_falsely_rejected':True,
    'wrong_oracle_semantically_identified':True,'frozen_and_review_bytes_unchanged':True,
    'native_shorthand_probe_failed_before_execution':True,
    'migration_implemented':False,'runtime_token_or_dollar_comparison':'unknown'}
write('final-summary',summary)

reports=[ROOT/'STAGE29_ARCHITECTURE_DECISION.md',ROOT/'STAGE29_SIMPLIFICATION_PLAN.md']
excluded={'workspace-before.json','workspace-after.json','original-after.json','delivery-receipt.json','evidence-manifest.json'}
paths=reports+sorted(p for p in E.rglob('*') if p.is_file() and p.name not in excluded and p.suffix in ('.json','.md','.py','.txt','.xml'))
manifest={p.relative_to(ROOT).as_posix():{'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size} for p in paths}
write('evidence-manifest',manifest)
archive=ROOT/'stage29-delivery.zip'
with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in paths+[E/'evidence-manifest.json']: z.write(p,p.relative_to(ROOT).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for name,entry in manifest.items(): assert sha(z.read(name))==entry['sha256']
write('delivery-receipt',{'archive':str(archive),'sha256':sha(archive.read_bytes()),'bytes':archive.stat().st_size,
    'manifest_entries':len(manifest),'zip_members':len(manifest)+1,'crc_and_member_hashes_verified':True,
    'excluded':'Old archives/repos, Stage 29 scratch/canaries, redundant full workspace/after manifests, receipt itself'})
print(json.dumps(summary,indent=2))
print('archive bytes:',archive.stat().st_size)
