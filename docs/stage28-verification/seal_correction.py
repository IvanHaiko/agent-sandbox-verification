"""Preserve the pre-exposure syntax defect and seal the corrected evaluator."""
import ast
import json
import time
import experiment as bench

e=bench.E
bench.ex.require(not (e/'A').exists() and not (e/'B').exists(),'Candidate exposure already occurred')
ast.parse((e/'test_external_acceptance.py').read_text())
result=bench.evaluate(e,'baseline-external-corrected',e/'test_external_acceptance.py',{})
bench.ex.require(result['tests']>40 and result['failed']>0 and result['errors']==0,'Corrected baseline control must execute without errors')
receipt={'at':time.time(),'classification':'Shared evaluator syntax defect before candidate exposure',
 'original_suite':'test_external_acceptance.original.py','original_result':'baseline-external.json',
 'original_freeze':'freeze.original.json','correction':'One closing list bracket; no contract or assertion changes',
 'candidate_exposure':False,'corrected_baseline':result,
 'effective_external_sha256':bench.ex.digest((e/'test_external_acceptance.py').read_bytes()),
 'original_sha256':bench.ex.digest((e/'test_external_acceptance.original.py').read_bytes()),
 'limitation':'Original frozen evaluator could not collect. Both candidates use the same corrected, resealed suite established before either candidate existed.'}
bench.ex.save(e,'evaluator-correction',receipt)
freeze=json.loads((e/'freeze.json').read_text())
freeze['original_freeze_preserved']='freeze.original.json'
freeze['pre_exposure_correction']='evaluator-correction.json'
freeze['effective_seal_at']=time.time()
freeze['sha256']['test_external_acceptance.py']=receipt['effective_external_sha256']
bench.ex.save(e,'freeze',freeze)
bench.ex.save(e,'interventions',[receipt])
print(json.dumps(receipt,indent=2))
