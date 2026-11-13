"""Read-only confirmation after all benchmark-owned resources were stopped/removed."""
import json
from pathlib import Path
import time

e=Path(__file__).resolve().parent
runtime=json.loads((e/'runtime.json').read_text())
paths={runtime['root'],runtime['database_workspace'],
       json.loads((e/'A/prepared.json').read_text())['workspace'],
       json.loads((e/'B/failed-cleanup-links.json').read_text())['workspace']}
for role in ('implementer','independent_tester','reviewer'):
    paths.add(json.loads((e/'B'/f'{role}-execution.json').read_text())['workspace'])
result={'at':time.time(),'owned_paths_absent':{p:not Path(p).exists() for p in sorted(paths)},
        'recorded_postmaster_pid':runtime['postmaster_pid'],
        'recorded_postmaster_pid_absent':not Path('/proc',str(runtime['postmaster_pid'])).exists()}
assert all(result['owned_paths_absent'].values()) and result['recorded_postmaster_pid_absent']
(e/'host-cleanup-audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
