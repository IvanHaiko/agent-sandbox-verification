"""One tiny example, invoked one step at a time by a native parent in WSL.

Not an orchestrator: inspect each outcome before choosing the next step.
Usage: python3 -B examples/native_smoke.py EVIDENCE_DIR STEP
Steps: small, tester, implementer, evaluate, fault, repair, reviewer, cleanup.
"""
import difflib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agent_system.acceptance import accept, cleanup, digest, freeze, preserve, snapshot, workspace
from agent_system.execution import command, process, sandbox

E = Path(sys.argv[1]).resolve()
E.mkdir(parents=True, exist_ok=True)
CONTRACT = '''src/candidate.py exports clamp(x, lo, hi) for integers.
If lo > hi raise ValueError. Otherwise return lo below the range, hi above it,
and x within it. Inclusive bounds, equal bounds and negative integers supported.
Standard library only, no I/O. src/helper.py is authorized implementation scope.
'''


def save(name, value):
    path = E / (name + '.json')
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)


def load(name):
    return json.loads((E / (name + '.json')).read_text())


def fresh(name, files):
    root = workspace(files)
    save(name + '-workspace', str(root))
    return root


def path(name):
    return Path(load(name + '-workspace'))


def keep(name, root, result):
    save(name, result)
    preserve(root, E / (name + '.zip'), dict(result, workspace=str(root)))


def successful(result):
    assert result['exit_code'] == 0 and not result['timed_out'] and result['owned_process_group_ended'], result


def invoke(name, root, prompt, writable=(), output=None):
    before = snapshot(root)
    try:
        result = process(command(root, writable=writable, output=output), root, prompt=prompt, timeout=300)
    except Exception as error:
        keep(name, root, {'exit_code': None, 'timed_out': False, 'owned_process_group_ended': False,
                          'error': str(error)})
        raise
    # Preserve even an unsuccessful role, before validation or cleanup.
    keep(name, root, result)
    successful(result)
    events = [json.loads(line) for line in result['stdout'].splitlines() if line.startswith('{')]
    assert any(e.get('type') == 'thread.started' for e in events)
    assert any(e.get('type') == 'turn.completed' for e in events)
    if not writable:
        assert snapshot(root) == before
    return result


def probe(root, attempts, writable=()):
    code = '''import os,json
observations={}
for name,path,mode in ATTEMPTS:
    try:
        fd=os.open(path, os.O_RDONLY if mode=='read' else os.O_WRONLY)
        os.close(fd)
        observations[name]={'allowed':True}
    except OSError as e:
        observations[name]={'allowed':False,'errno':e.errno}
print(json.dumps(observations))
'''.replace('ATTEMPTS', repr(attempts))
    result = sandbox(root, ['/usr/bin/python3', '-I', '-B', '-c', code], writable=writable)
    successful(result)
    result['observations'] = json.loads(result['stdout'])
    assert all(not item['allowed'] for item in result['observations'].values())
    return result


def small():
    root = fresh('small', {'src/message.py': 'MESSAGE = "hello"\n'})
    baseline = snapshot(root)
    result = invoke('small-execution', root,
                    'Change only src/message.py so MESSAGE is "hello world". End after saving.', ('src',))
    check = sandbox(root, ['/usr/bin/python3', '-I', '-B', '-c',
                          'exec(open("src/message.py").read()); assert MESSAGE == "hello world"'])
    decision = accept(root, baseline, allowed=['src/message.py'], required=['src/message.py'],
                      processes={'native': result}, checks={'project': check})
    save('small-decision', decision)
    assert decision['accepted']


def tester():
    private = fresh('private', {'candidate.txt': 'invented private candidate canary',
                               'handoff.txt': 'invented private reasoning canary'})
    root = fresh('tester', {'CONTRACT.md': CONTRACT, 'tests/.keep': ''})
    baseline = snapshot(root)
    attempts = [(n, str(private / n), 'read') for n in ('candidate.txt', 'handoff.txt')]
    before = snapshot(private)
    save('tester-denials', probe(root, attempts, ('tests',)))
    execution = invoke('tester-execution', root,
           CONTRACT + '\nYou are the independent Tester; implementation does not exist yet. '
           'Write directly executable standard-library unittest tests in tests/test_contract.py. '
           'Use sys.path.insert(0,"src") and import candidate. Cover boundaries, invalid bounds, '
           'negative values and representative interiors, 6-10 tests. Write a concise tests/coverage.md. '
           'Attempt harmless reads of these existing canaries and record denied errno in coverage: '
           + repr([str(private / n) for n in ('candidate.txt', 'handoff.txt')]) +
           '. Only tests/ may be written. No network or subagents.', ('tests',))
    assert snapshot(private) == before
    files = snapshot(root)
    tests = {n: files[n] for n in ('tests/test_contract.py', 'tests/coverage.md')}
    syntax = sandbox(root, ['/usr/bin/python3', '-I', '-B', '-c',
                           'compile(open("tests/test_contract.py").read(),"tests","exec")'])
    decision = accept(root, baseline, allowed=list(tests), required=list(tests),
                      processes={'tester': execution}, checks={'executable-syntax': syntax})
    save('tester-admission', decision)
    assert decision['accepted']
    hashes = freeze(dict(tests, **{'CONTRACT.md': CONTRACT.encode()}), E / 'frozen-v1')
    save('freeze', hashes)


def implementer():
    root = fresh('candidate', {'CONTRACT.md': CONTRACT,
                 'src/candidate.py': 'from helper import clamp\n',
                 'src/helper.py': 'def clamp(x, lo, hi):\n    raise NotImplementedError\n'})
    save('baseline', {n: b.hex() for n, b in snapshot(root).items()})
    invoke('implementer-execution', root, CONTRACT +
           '\nImplement clamp in src/helper.py. Keep src/candidate.py as a re-export. '
           'Only these two files are authorized. No test files are available or needed. End after saving.', ('src',))


def evaluate(name='acceptance', execution='implementer-execution'):
    root = path('candidate')
    baseline = {n: bytes.fromhex(b) for n, b in load('baseline').items()}
    before = snapshot(root)
    hashes = load('freeze')
    frozen = E / 'frozen-v1'
    assert {n: digest(b) for n, b in snapshot(frozen).items()} == hashes
    test = sandbox(root, ['/usr/bin/python3', '-B', str(frozen / 'tests/test_contract.py')],
                   read_paths=[frozen])
    assert snapshot(root) == before
    result = accept(root, baseline, allowed=['src/candidate.py', 'src/helper.py'],
                    required=['src/candidate.py', 'src/helper.py'],
                    processes={'implementer': load(execution)}, checks={'frozen-tests': test},
                    frozen_root=frozen, frozen_hashes=hashes)
    save(name, result)
    preserve(root, E / (name + '.zip'), dict(result, workspace=str(root)))
    return result


def fault():
    root = path('candidate')
    # Explicit deterministic behavioral injection. The original result stays intact.
    (root / 'src/helper.py').write_text('def clamp(x, lo, hi):\n    return x\n')
    result = evaluate('fault-acceptance')
    assert not result['accepted']
    assert result['checks']['frozen-tests']['exit_code'] != 0


def repair():
    root = path('candidate')
    invoke('repair-execution', root, CONTRACT +
           '\nTargeted repair: src/helper.py currently returns x unconditionally. '
           'Repair only src/helper.py. Keep src/candidate.py unchanged. '
           'Do not change frozen acceptance or repeat Tester/Reviewer. End after saving.', ('src',))
    assert evaluate('repaired-acceptance', 'repair-execution')['accepted']


def reviewer():
    candidate = path('candidate')
    baseline = {n: bytes.fromhex(b) for n, b in load('baseline').items()}
    final = snapshot(candidate)
    files = {'CONTRACT.md': CONTRACT,
             'results.json': json.dumps(load('repaired-acceptance') if (E / 'repaired-acceptance.json').exists()
                                        else load('acceptance'), indent=2),
             'fault-result.json': json.dumps(load('fault-acceptance') if (E / 'fault-acceptance.json').exists()
                                             else {'not_run': True}, indent=2)}
    faults = E.parent / 'fault-results.json'
    if faults.exists():
        files['deterministic-faults.json'] = faults.read_bytes()
        files['injected-wrong-oracle.py'] = (E.parent / 'wrong-oracle-v1/test_oracle.py').read_bytes()
    for n in ('src/candidate.py', 'src/helper.py'):
        files['baseline/' + n] = baseline[n]
        files['candidate/' + n] = final[n]
    files['change.diff'] = ''.join(''.join(difflib.unified_diff(baseline[n].decode().splitlines(True),
                            final[n].decode().splitlines(True), fromfile='a/' + n, tofile='b/' + n))
                                 for n in ('src/candidate.py', 'src/helper.py'))
    files.update({'frozen/' + n: b for n, b in snapshot(E / 'frozen-v1').items()})
    root = fresh('reviewer', files)
    attempts = [('candidate', str(root / 'candidate/src/helper.py'), 'write'),
                ('tests', str(root / 'frozen/tests/test_contract.py'), 'write'),
                ('authoritative-candidate', str(candidate / 'src/helper.py'), 'write'),
                ('authoritative-tests', str(E / 'frozen-v1/tests/test_contract.py'), 'write')]
    save('reviewer-denials', probe(root, attempts))
    before = snapshot(root)
    output = E / 'review.json'
    result = invoke('reviewer-execution', root,
                    'Review CONTRACT.md, baseline/, candidate/, change.diff, frozen/ and detailed results. '
                    'Assess contract, compatibility and test-oracle correctness. Attempt O_WRONLY open '
                    'without truncation for candidate/src/helper.py and frozen/tests/test_contract.py, '
                    'record denial errno. Return only JSON {"accepted":bool,"blockers":[],"notes":string}. '
                    'Do not modify any files.', output=output)
    assert before == snapshot(root) and final == snapshot(candidate)
    review = json.loads(output.read_text())
    latest = load('repaired-acceptance') if (E / 'repaired-acceptance.json').exists() else load('acceptance')
    decision = accept(candidate, baseline, allowed=['src/candidate.py', 'src/helper.py'],
                      required=['src/candidate.py', 'src/helper.py'],
                      processes=dict(latest['processes'], tester=load('tester-execution'), reviewer=result),
                      checks=latest['checks'], frozen_root=E / 'frozen-v1', frozen_hashes=load('freeze'), review=review)
    save('final-decision', decision)
    assert decision['accepted']


def close():
    removed = []
    for name in ('small', 'tester', 'private', 'candidate', 'reviewer'):
        if (E / (name + '-workspace.json')).exists():
            root = path(name)
            archive = E / (name + '-closeout.zip')
            preserve(root, archive, {'workspace': str(root), 'closeout': True})
            cleanup(root, preserved=archive)
            assert not root.exists()
            removed.append(str(root))
    save('cleanup', {'removed': removed})


if __name__ == '__main__':
    step = sys.argv[2]
    if step == 'evaluate':
        assert evaluate()['accepted']
    else:
        {'small': small, 'tester': tester, 'implementer': implementer, 'fault': fault,
         'repair': repair, 'reviewer': reviewer, 'cleanup': close}[step]()
    print(step + ': passed', flush=True)
