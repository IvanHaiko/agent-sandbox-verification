"""Optional read-only role instructions and structured artifact contracts."""
import json
import jsonschema
from . import artifacts as flow
from .artifacts import digest

TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 2500}
STRINGS = {'type': 'array', 'items': TEXT, 'maxItems': 6}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


REVIEW_SCHEMA = obj({'recommendation': {'type': 'string', 'enum': ['accept', 'reject', 'request-fix']},
    'blockers': STRINGS,
    'findings': {'type': 'array', 'maxItems': 6, 'items': obj({
        'id': TEXT, 'criterion': {'type': 'integer', 'minimum': 1, 'maximum': 10},
        'severity': {'type': 'string', 'enum': ['blocking', 'nonblocking', 'info']},
        'description': TEXT, 'evidence': TEXT, 'already_established_by_acceptance': {'type': 'boolean'}})},
    'rationale': TEXT})

def architect_schema(contract):
    return obj({
        'public_interface': {'type': 'string', 'enum': [contract.TASK['public_interface']]},
        'allowed_mutation_scope': {'type': 'array', 'minItems': 1, 'maxItems': 1,
                                   'items': {'type': 'string', 'enum': [contract.TASK['file']]}},
        'acceptance_criteria': {'type': 'array', 'minItems': len(contract.CRITERIA),
            'maxItems': len(contract.CRITERIA), 'items': {'type': 'string', 'enum': contract.CRITERIA}},
        'constraints': {'type': 'array', 'minItems': len(contract.TASK['constraints']),
            'maxItems': len(contract.TASK['constraints']),
            'items': {'type': 'string', 'enum': contract.TASK['constraints']}},
        'clarifications': {'type': 'array', 'maxItems': 4, 'items': obj({
            'rules': {'type': 'array', 'minItems': 1, 'maxItems': 4,
                      'items': {'type': 'integer', 'minimum': 1, 'maximum': 10}}, 'clarification': TEXT})},
        'risks': STRINGS})



def validate_semantic(data, schema, contract):
    value = contract.strict_json(data.decode('utf-8'))
    jsonschema.Draft202012Validator(schema).validate(value)
    if 'allowed_mutation_scope' in schema['properties']:
        for key, expected in {'public_interface': contract.TASK['public_interface'],
                             'allowed_mutation_scope': [contract.TASK['file']],
                             'acceptance_criteria': contract.CRITERIA,
                             'constraints': contract.TASK['constraints']}.items():
            flow.require(value[key] == expected, 'Architect changed original ' + key)
    if schema is REVIEW_SCHEMA and value['recommendation'] == 'accept':
        flow.require(not value['blockers'] and not any(f['severity'] == 'blocking' for f in value['findings']),
                     'Reviewer accept contradicts blockers')
    return {'valid': True, 'schema_valid': True}


def semantic_role(runner, directory, trial_id, role, bundle, schema, instruction, owned, contract):
    text = json.dumps(bundle, indent=2)
    prompt = instruction + '\nRead role-input.md, TASK.json, bundle.json and schema.json only.\n' + text
    workspace = flow.owned_workspace({'role-input.md': prompt,
        'TASK.json': json.dumps(contract.TASK, indent=2), 'bundle.json': text,
        'schema.json': json.dumps(schema, indent=2)})
    owned.append(workspace)
    flow.archive(directory, role + '-input.md', prompt.encode())
    record = None
    try:
        record = runner.run_read_only(trial_id=trial_id, role=role, workspace=workspace,
            output=directory / (role + '-result.json'), prompt=prompt,
            verify=lambda data: validate_semantic(data, schema, contract))
        flow.save(directory, role + '-execution', record)
        flow.require(record['execution_status'] == 'completed', role + ' native/schema/scope failure')
        return record, contract.strict_json((directory / (role + '-result.json')).read_text())
    finally:
        flow.cleanup(workspace)
        if record is not None:
            record['cleanup_passed'] = not workspace.exists()
            flow.save(directory, role + '-execution', record)


def review(runner, directory, assessment, owned, canonical, contract):
    handoff = json.loads((directory / 'implementer-handoff.json').read_text())
    freeze = json.loads((directory / 'test-freeze.json').read_text())
    flow.require_frozen(directory, freeze)
    candidate_hash = digest((directory / 'candidate.py').read_bytes())
    bundle = {'task': contract.TASK, 'canonical_contract': canonical,
        'candidate_diff': handoff['diff'], 'implementation_handoff': handoff,
        'frozen_test_summary': {'design_sha256': freeze['design_sha256'], 'case_count': assessment['case_count'],
            'candidate_blind_before_freeze': True, 'frozen_before_exposure': True},
        'deterministic_acceptance': assessment['acceptance'],
        'scope_interface_evidence': {'implementation_scope_valid': True,
                                    'interface': handoff['interface_check']}}
    record, result = semantic_role(runner, directory, assessment['trial_id'], 'reviewer', bundle,
        REVIEW_SCHEMA, 'Role: Reviewer. Review only the supplied contract, diff and Controller artifact evidence.\n'
        'You have no prior role conversation or hidden implementation context. Your entire workspace is read-only.\n'
        'Do not modify implementation, tests or inputs, run acceptance again, read other workspaces, use network,\n'
        'credentials or subagents. Return only JSON matching schema.json through native structured output.\n'
        'Recommend accept/reject/request-fix. Identify concrete in-scope defects, missing evidence or contract\n'
        'risks; do not invent requirements. Report blockers and findings, distinguishing facts already established\n'
        'by deterministic acceptance from anything additional you can substantiate. No implementation changes.', owned, contract)
    assessment['roles'].append(record)
    flow.require(digest((directory / 'candidate.py').read_bytes()) == candidate_hash, 'Reviewer changed candidate archive')
    flow.require_frozen(directory, freeze)
    return result


def load_canonical(directory, contract):
    """Verify Controller normalization without permitting any change to the frozen task."""
    canonical = json.loads((directory / 'normalized-contract.json').read_text())
    for key, value in contract.TASK.items():
        flow.require(canonical.get(key) == value, 'Controller canonical contract changed original ' + key)
    flow.require(set(canonical) <= set(contract.TASK) | {'clarifications', 'risks'}, 'Unapproved contract fields')
    receipt = json.loads((directory / 'contract-normalization.json').read_text())
    flow.require(receipt['authority'] == 'Controller' and receipt['original_criteria_preserved'],
                 'Controller normalization required')
    flow.require(receipt['canonical_sha256'] == digest((directory / 'normalized-contract.json').read_bytes()),
                 'Canonical contract hash mismatch')
    return canonical


