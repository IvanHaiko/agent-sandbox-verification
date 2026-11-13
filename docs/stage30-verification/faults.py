"""Compact deterministic fault injection, not real agent execution."""
import json
from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agent_system.acceptance import accept, cleanup, freeze, preserve, snapshot, workspace
from agent_system.execution import process, sandbox

E = Path(__file__).resolve().parent


def main():
    root = workspace({'src/main.py': 'from helper import clamp\n',
                      'src/helper.py': 'def clamp(x,lo,hi):\n    return min(max(x,lo),hi)\n'})
    baseline = snapshot(root)
    observed = process(['/usr/bin/python3', '-c', 'pass'], root)
    outcomes = {}
    def decide(name, proc=observed, check=observed, **extra):
        outcomes[name] = accept(root, baseline, allowed=['src/helper.py'],
                               required=['src/main.py', 'src/helper.py'],
                               processes={'native': proc}, checks={'test': check}, **extra)
        return outcomes[name]
    (root / 'src/helper.py').write_text('def clamp(x,lo,hi):\n    return max(lo,min(x,hi))\n')
    assert decide('secondary-only')['accepted']
    (root / 'src/unapproved.py').write_bytes(b'unauthorized sibling bytes')
    assert not decide('sibling')['accepted']
    (root / 'src/unapproved.py').unlink()
    # An incorrect frozen expectation stays failed; implementation is not edited to match.
    wrong = E / 'wrong-oracle-v1'
    hashes = freeze({'test_oracle.py': b'import sys\nsys.path.insert(0,"src")\nfrom helper import clamp\nassert clamp(5,0,3)==5\n'}, wrong)
    oracle = sandbox(root, ['/usr/bin/python3', '-B', str(wrong / 'test_oracle.py')], read_paths=[wrong])
    assert not decide('wrong-oracle', check=oracle, frozen_root=wrong, frozen_hashes=hashes)['accepted']
    outcomes['oracle-adjudication'] = {'status': 'escalated; no superseding version approved',
        'issue': 'The public clamp contract requires 3 for (5,0,3); this injected oracle expects 5.',
        'original_failure_preserved': True, 'implementation_changed_to_match_oracle': False}
    (root / 'src/helper.py').write_bytes(b'def broken(')
    failed = process(['/usr/bin/python3', '-c', 'raise SystemExit(17)'], root)
    malformed = sandbox(root, ['/usr/bin/python3', '-B', '-c', 'compile(open("src/helper.py").read(),"helper.py","exec")'])
    assert not decide('malformed-exit17', proc=failed, check=malformed)['accepted']
    timeout = process(['/usr/bin/python3', '-c', 'import time; time.sleep(60)'], root, timeout=.2)
    assert timeout['timed_out'] and timeout['owned_process_group_ended']
    outcomes['timeout'] = timeout
    archive = E / 'rejected-partial.zip'
    preserve(root, archive, {'workspace': str(root), 'results': outcomes})
    cleanup(root, preserved=archive)
    with zipfile.ZipFile(archive) as z:
        assert z.read('files/src/helper.py') == b'def broken('
    outcomes['preservation'] = {'workspace_removed': not root.exists(), 'exact_partial_bytes_survived': True}
    (E / 'fault-results.json').write_text(json.dumps(outcomes, indent=2))
    print('Deterministic faults rejected; secondary repair allowed; partial bytes survive cleanup.')


if __name__ == '__main__':
    main()
