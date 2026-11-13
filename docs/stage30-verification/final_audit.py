"""Verify built package and remove only explicitly recorded Stage 30 build/test scratch."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
E = Path(__file__).resolve().parent
wheel = E / 'package/codex_agent_system-2.0.0-py3-none-any.whl'
with zipfile.ZipFile(wheel) as archive:
    members = archive.namelist()
    sources = [n for n in members if n.endswith('.py')]
    assert set(sources) == {'agent_system/__init__.py', 'agent_system/acceptance.py', 'agent_system/execution.py'}
    assert all(archive.read(n) == (ROOT / n).read_bytes() for n in sources)
    metadata = archive.read('codex_agent_system-2.0.0.dist-info/METADATA').decode()
    assert 'jsonschema' not in metadata
sys.path.insert(0, str(wheel))
import agent_system
from agent_system import acceptance, execution
assert '.whl/' in agent_system.__file__
assert callable(acceptance.accept) and callable(execution.sandbox)
removed = []
for relative in ('.test-tmp/stage30-support', '.test-tmp/stage30-build', 'build', 'codex_agent_system.egg-info'):
    target = ROOT / relative
    if target.exists():
        assert target.resolve().is_relative_to(ROOT) and not target.is_symlink()
        shutil.rmtree(target)
        removed.append(str(target))
for name in ('stage30-support', 'stage30-final-support', 'stage30-shutdown-support'):
    target = Path('/tmp') / name
    if target.exists():
        assert target.resolve().parent == Path('/tmp') and not target.is_symlink()
        shutil.rmtree(target)
        removed.append(str(target))
inventory = json.loads((E / 'inventory.json').read_text())
inventory['after']['test_lines'] = sum(len(p.read_bytes().splitlines()) for p in (ROOT / 'tests').glob('test_*.py'))
for item in inventory['active_source']:
    assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']
(E / 'inventory.json').write_text(json.dumps(inventory, indent=2))
role_cleanup = json.loads((E / 'native/cleanup.json').read_text())
assert all(not Path(p).exists() for p in role_cleanup['removed'])
historical = json.loads((E / 'historical-integrity.json').read_text())
assert historical['unchanged']
assert json.loads((E / 'original-before.json').read_text()) == json.loads((E / 'original-after.json').read_text())
(E / 'final-audit.json').write_text(json.dumps({'built_wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
    'package_sources': sources, 'zip_import_passed': True, 'runtime_dependencies': [],
    'scratch_removed': removed, 'all_role_workspaces_removed': True,
    'original_checkout_index_registry_unchanged': True, 'historical_evidence': historical}, indent=2))
print('Built package imports; active source hashes match; owned test/build scratch removed; original/history unchanged.')
