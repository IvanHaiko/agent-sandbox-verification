"""Post-removal integrity/evidence audit; no model sessions or orchestration."""
import ast
import json
from pathlib import Path
import sys
import tomllib
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from agent_system.acceptance import accept, digest, snapshot
from agent_system.execution import sandbox


def main():
    native = E / 'native'
    def load(name):
        return json.loads((native / (name + '.json')).read_text())
    candidate = Path(load('candidate-workspace'))
    frozen = native / 'frozen-v1'
    hashes = load('freeze')
    final = load('final-decision')
    assert final['accepted']
    assert final['changed_files'] == ['src/helper.py']
    assert {n: digest(b) for n, b in snapshot(candidate).items()} == final['final_hashes']
    before = snapshot(candidate)
    code = 'compile(open("src/helper.py").read(),"helper","exec"); print("final candidate syntax valid")'
    syntax = sandbox(candidate, ['/usr/bin/python3', '-I', '-B', '-c', code])
    assert syntax['exit_code'] == 0 and syntax['owned_process_group_ended']
    test = sandbox(candidate, ['/usr/bin/python3', '-B', str(frozen / 'tests/test_contract.py')], read_paths=[frozen])
    decision = accept(candidate, {n: bytes.fromhex(b) for n, b in load('baseline').items()},
                      allowed=['src/candidate.py', 'src/helper.py'], required=['src/candidate.py', 'src/helper.py'],
                      processes=final['processes'], checks={'frozen-tests': test, 'syntax': syntax},
                      frozen_root=frozen, frozen_hashes=hashes, review=final['review'])
    assert decision['accepted'] and snapshot(candidate) == before
    # Verify the Implementer's exact profile cannot write the authoritative freeze.
    probe_code = ('import os,json\np=' + repr(str(frozen / 'tests/test_contract.py')) +
                  '\ntry:\n fd=os.open(p,os.O_WRONLY)\n os.close(fd)\n raise RuntimeError("write allowed")'
                  '\nexcept OSError as e:\n print(json.dumps({"allowed":False,"errno":e.errno}))')
    denial = sandbox(candidate, ['/usr/bin/python3', '-I', '-B', '-c', probe_code], writable=['src'])
    assert denial['exit_code'] == 0 and denial['owned_process_group_ended']
    assert {n: digest(b) for n, b in snapshot(frozen).items()} == hashes
    tester = Path(load('tester-workspace'))
    actual = snapshot(tester)
    original = {n: b for n, b in actual.items() if not n.startswith('tests/')}
    original['tests/.keep'] = b''
    tester_admission = accept(tester, original,
        allowed=['tests/test_contract.py', 'tests/coverage.md'], required=['tests/test_contract.py', 'tests/coverage.md'],
        processes={'tester': load('tester-execution')}, checks={'syntax': sandbox(tester,
            ['/usr/bin/python3', '-I', '-B', '-c', 'compile(open("tests/test_contract.py").read(),"test","exec")'])})
    assert tester_admission['accepted']
    with (native / 'tester-admission.json').open('x') as stream:
        json.dump(tester_admission, stream, indent=2)
    (E / 'post-removal-checks.json').write_text(json.dumps({'decision': decision,
        'implementer-frozen-write-denial': denial, 'tester_scope_verified': True,
        'original_roles_replayed': False}, indent=2))
    with zipfile.ZipFile(E / 'source-rollback.zip') as archive:
        rollback = json.loads((E / 'rollback.json').read_text())
        assert digest((E / 'source-rollback.zip').read_bytes()) == rollback['archive_sha256']
        assert archive.testzip() is None
        assert all(digest(archive.read(n)) == h for n, h in rollback['files'].items())
        old_core = {n: archive.read(n) for n in archive.namelist() if n.startswith('agent_system/') and n.endswith('.py')}
    paths = [p for directory in ('agent_system', 'examples', 'project_tooling')
             for p in (ROOT / directory).rglob('*.py')]
    inventory = []
    for p in paths:
        data = p.read_bytes()
        tree = ast.parse(data)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append('.' * node.level + (node.module or ''))
        assert not any(any(bad in name for bad in ('controller', 'native_codex_linux', 'test_environment', 'validation.', 'jsonschema'))
                       for name in imports)
        inventory.append({'path': p.relative_to(ROOT).as_posix(), 'physical_lines': len(data.splitlines()),
                          'sha256': digest(data), 'imports': sorted(set(imports))})
    config = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    assert config['project']['dependencies'] == []
    tests = list((ROOT / 'tests').glob('test_*.py'))
    project = json.loads((E / 'project-direct/result.json').read_text())
    assert all(project[k] for k in ('passed', 'source_unchanged', 'postgres_stopped', 'postmaster_gone', 'workspaces_removed'))
    cases = list(ET.parse(E / 'project-direct/results.xml').getroot().iter('testcase'))
    assert len(cases) == 168 and not any(list(c) for c in cases)
    db = [c for c in cases if c.attrib.get('classname', '').endswith('_db')]
    (E / 'inventory.json').write_text(json.dumps({'before': {'all_active_files': rollback['active_source_files'],
        'all_active_lines': rollback['active_physical_lines'], 'package_files': len(old_core),
        'package_lines': sum(len(b.splitlines()) for b in old_core.values()), 'test_files': 5,
        'runtime_dependencies': ['jsonschema>=4.18,<5'], 'workflow_entry_points': 3,
        'other_runtime_control_probe_entry_points': 4}, 'after': {'all_active_files': len(paths),
        'all_active_lines': sum(item['physical_lines'] for item in inventory),
        'package_files': len([p for p in paths if p.parent.name == 'agent_system']),
        'package_lines': sum(item['physical_lines'] for item in inventory if item['path'].startswith('agent_system/')),
        'test_files': len(tests), 'test_lines': sum(len(p.read_bytes().splitlines()) for p in tests),
        'runtime_dependencies': [], 'workflow_entry_points': 0, 'standalone_examples': 1,
        'project_recipes': 1}, 'active_source': inventory, 'project_tests': len(cases), 'database_tests': len(db)}, indent=2))
    print('Post-removal frozen acceptance, permission denial, imports and rollback verified.')


if __name__ == '__main__':
    main()
