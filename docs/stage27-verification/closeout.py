"""Recorded evaluation cleanup correction and scheduled B review after adapter failure.

Does not change frozen experiment.py, acceptance tests, candidates, or original decisions.
"""
import json
from pathlib import Path
import shutil
import sys
import time

import experiment as ex


def correction_record():
    entries=json.loads((ex.E/'interventions.json').read_text())
    if entries:
        return
    entries.append({'at':time.time(), 'kind':'coordinator_evaluation_cleanup_correction',
        'cause':'Frozen Stage27 adapter called strict artifact cleanup with ordinary pytest scratch symlinks still present',
        'attribution':'Stage27 coordinator adapter defect; not a candidate defect or demonstrated existing framework defect',
        'original_result_preserved':'B/assessment.json and B/independent.json unchanged: 40 tests passed, cleanup raised Linked workspace entry',
        'correction':'Remove verified owned scratch subtree after archiving results, then invoke unchanged strict cleanup',
        'applied_to':'Both A and B shared evaluations, independent evaluations, and mutation controls equally',
        'candidate_or_suite_edits':False, 'role_retries':0,
        'extra_agents':0, 'additional_action':'Run originally scheduled B Reviewer once as failure closeout; do not resume or overwrite B workflow decision'})
    ex.save(ex.E,'interventions',entries)


def safe_evaluation_cleanup(workspace):
    workspace=Path(workspace)
    ex.require(workspace.parent==Path.home().resolve() and workspace.name.startswith('codex-role-')
               and not workspace.is_symlink(), 'Unexpected evaluation cleanup root')
    scratch=workspace/'scratch'
    if scratch.exists():
        ex.require(not scratch.is_symlink() and scratch.resolve()==workspace/'scratch', 'Unexpected scratch root')
        shutil.rmtree(scratch)
    ex.cleanup(workspace)


def review():
    correction_record()
    out=ex.E/'B'
    ex.require(not (out/'reviewer-execution.json').exists(),'Reviewer already consumed')
    manifest=json.loads((out/'candidate-manifest.json').read_text())
    candidate={p:(out/'candidate'/p).read_bytes() for p in manifest}
    acceptance={'functional_result':json.loads((out/'independent.json').read_text()),
                'workflow_failure':json.loads((out/'assessment.json').read_text())['failure'],
                'context':'Scheduled review after coordinator adapter cleanup failure. Original Controller rejection remains. No external candidate results provided.'}
    files={'original/'+p:b for p,b in ex.source().items() if p.startswith('src/')}
    files.update({'candidate/'+p:b for p,b in dict(ex.source(),**candidate).items() if p.startswith('src/')})
    files.update({'TASK.md':ex.task(),'TASK.json':json.dumps({'task':ex.task().decode()}).encode(),
        'role-input.md':ex.REVIEW_PROMPT.encode(),'review-rubric.md':(ex.E/'review-rubric.md').read_bytes(),
        'candidate.patch':(out/'implementation.patch').read_bytes(),'acceptance.json':json.dumps(acceptance).encode(),
        'test-design.json':(out/'frozen-test-design.json').read_bytes(),
        'schema.json':json.dumps(ex.REVIEW_SCHEMA).encode()})
    ws=ex.owned_workspace(files)
    try:
        record=ex.runner().run_read_only(trial_id='stage27-B-closeout',role='reviewer',workspace=ws,
            output=out/'reviewer-result.json',prompt=ex.REVIEW_PROMPT,
            verify=lambda b:ex.validate_json(b,ex.REVIEW_SCHEMA),timeout=360)
        record['failure_closeout']=True
        ex.save(out,'reviewer-execution',record)
    finally:
        ex.cleanup(ws)
    print('SCHEDULED B REVIEW FINISHED; original workflow result retained',flush=True)


def evaluate():
    correction_record()
    # Only the cleanup boundary changes; every frozen test and candidate byte is preserved.
    original_cleanup=ex.cleanup
    def wrapper(ws):
        ex.require(Path(ws).parent==Path.home().resolve() and Path(ws).name.startswith('codex-role-')
                   and not Path(ws).is_symlink(),'Unexpected workspace')
        scratch=Path(ws)/'scratch'
        if scratch.exists():
            ex.require(not scratch.is_symlink() and scratch.resolve()==Path(ws)/'scratch','Unexpected scratch')
            shutil.rmtree(scratch)
        original_cleanup(ws)
    ex.cleanup=wrapper
    ex.evaluate_all()


def retained_cleanup():
    # The failed evaluation root was independently identified before this code was authored.
    ws=Path('/home/ivan/codex-role-0ceb46u5')
    ex.require(ws.is_dir() and (ws/'tests/test_stage27_evaluation.py').read_bytes()==
               (ex.E/'B/frozen-acceptance.py').read_bytes(),'Retained evaluation root identity mismatch')
    links={str(p):str(p.readlink()) for p in ws.rglob('*') if p.is_symlink()}
    ex.save(ex.E/'B','failed-cleanup-links',{'workspace':str(ws),'links':links})
    safe_evaluation_cleanup(ws)
    ex.save(ex.E/'B','failed-cleanup-closeout',{'workspace_removed':not ws.exists(),
        'original_assessment_unchanged':True,'scratch_removed_after_results_archived':True})


if __name__=='__main__':
    {'review':review,'evaluate':evaluate,'retained-cleanup':retained_cleanup}[sys.argv[1]]()
