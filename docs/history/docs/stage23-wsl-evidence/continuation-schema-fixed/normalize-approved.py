"""Write only explicitly Controller-reviewed Architect clarifications; no inference."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('phase', choices=['architect', 'full'])
parser.add_argument('number', type=int, choices=[1, 2])
parser.add_argument('--clarifications', required=True)
parser.add_argument('--risks', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parent
directory = root / args.phase / (args.phase + '-' + str(args.number))
proposal_bytes = (directory / 'architect-result.json').read_bytes()
proposal = json.loads(proposal_bytes)
source = json.loads((root.parent / 'minimal/minimal-1/frozen-task.json').read_text())
assert proposal['public_interface'] == source['public_interface']
assert proposal['allowed_mutation_scope'] == [source['file']]
assert proposal['acceptance_criteria'] == source['acceptance_criteria']
assert proposal['constraints'] == source['constraints']
select = lambda value: [] if value == 'none' else [int(i) for i in value.split(',')]
clarifications, risks = select(args.clarifications), select(args.risks)
canonical = {**source,
    'clarifications': [proposal['clarifications'][i] for i in clarifications],
    'risks': [proposal['risks'][i] for i in risks]}
data = json.dumps(canonical, indent=2).encode()
output = directory / 'normalized-contract.json'
assert not output.exists()
output.write_bytes(data)
receipt = {'authority': 'Controller', 'original_criteria_preserved': True,
    'canonical_sha256': hashlib.sha256(data).hexdigest(),
    'proposal_sha256': hashlib.sha256(proposal_bytes).hexdigest(),
    'accepted_clarification_indices': clarifications, 'accepted_risk_indices': risks,
    'scope_constraints_and_interface_unchanged': True,
    'review_basis': 'Primary Controller reviewed each selected item against original rules 1-10; '
        'only in-scope rule interactions and compact contract risks selected. No added requirement/code/algorithm.'}
(directory / 'contract-normalization.json').write_text(json.dumps(receipt, indent=2))
print('Controller canonical contract saved; original criteria/scope/interface unchanged')
