"""Record explicit user retry and reuse only the already successful Architect artifact."""
import json
from pathlib import Path
import time

from agent_system.artifacts import save, require
from validation.steam_workflow import source_fingerprint

directory = Path(__file__).resolve().parent
prior = directory.parent / 'native-run'
before = json.loads((directory / 'original-before.json').read_text())
require(before == source_fingerprint(Path('/mnt/c/Users/4ivan/steam-etl')),
        'Original repository changed between attempts')
prepared = json.loads((directory / 'preparation-assessment.json').read_text())
prepared['started_at'] = time.time()
prepared['resumed_from'] = str(prior)
prepared['architect_reused'] = True
save(directory, 'preparation-assessment', prepared)
save(directory, 'retry-authorization', {'authorization': 'Human explicitly requested another attempt and proper testing',
    'prior_outcome': 'FAIL', 'prior_evidence': str(prior), 'automatic_retry': False,
    'architect': 'Previously completed read-only proposal reused unchanged; no additional Architect model call',
    'isolation_change': 'Controller acceptance only: unshare user/network namespace, native filesystem sandbox, Unix IPC enabled. Model roles retain network=false and no database access.',
    'proof': 'socket-namespace-ipc.json demonstrates allowed private filesystem IPC and inaccessible host pathname/abstract/TCP services',
    'started_at': prepared['started_at']})
(prior / 'first-attempt-assessment.md').write_bytes((directory.parents[2] / 'STAGE25_REAL_WORLD_CODING_ASSESSMENT.md').read_bytes())
