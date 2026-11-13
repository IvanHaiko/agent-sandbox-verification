"""Sequential gated Reviewer, Architect and full-chain trials on the accepted WSL backend."""
import argparse
import json
from pathlib import Path
import sys

import jsonschema
import stage23_wsl_workflow as flow
from agent_system.native_codex_linux import NativeLinuxCodexRunner, digest

ROOT = flow.ROOT
OUT = ROOT / 'docs/stage23-wsl-evidence/continuation'
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

ARCHITECT_SCHEMA = obj({
    'public_interface': {'type': 'string', 'enum': [flow.contract.TASK['public_interface']]},
    'allowed_mutation_scope': {'type': 'array', 'minItems': 1, 'maxItems': 1,
                               'items': {'type': 'string', 'enum': [flow.TARGET]}},
    'acceptance_criteria': {'type': 'array', 'minItems': len(flow.contract.CRITERIA),
        'maxItems': len(flow.contract.CRITERIA), 'items': {'type': 'string', 'enum': flow.contract.CRITERIA}},
    'constraints': {'type': 'array', 'minItems': len(flow.contract.TASK['constraints']),
        'maxItems': len(flow.contract.TASK['constraints']),
        'items': {'type': 'string', 'enum': flow.contract.TASK['constraints']}},
    'clarifications': {'type': 'array', 'maxItems': 4, 'items': obj({
        'rules': {'type': 'array', 'minItems': 1, 'maxItems': 4,
                  'items': {'type': 'integer', 'minimum': 1, 'maximum': 10}}, 'clarification': TEXT})},
    'risks': STRINGS})


def validate_semantic(data, schema):
    value = flow.contract.strict_json(data.decode('utf-8'))
    jsonschema.Draft202012Validator(schema).validate(value)
    if schema is ARCHITECT_SCHEMA:
        for key, expected in {'public_interface': flow.contract.TASK['public_interface'],
                             'allowed_mutation_scope': [flow.TARGET],
                             'acceptance_criteria': flow.contract.CRITERIA,
                             'constraints': flow.contract.TASK['constraints']}.items():
            flow.require(value[key] == expected, 'Architect changed original ' + key)
    if schema is REVIEW_SCHEMA and value['recommendation'] == 'accept':
        flow.require(not value['blockers'] and not any(f['severity'] == 'blocking' for f in value['findings']),
                     'Reviewer accept contradicts blockers')
    return {'valid': True, 'schema_valid': True}


def semantic_role(runner, directory, trial_id, role, bundle, schema, instruction, owned):
    text = json.dumps(bundle, indent=2)
    prompt = instruction + '\nRead role-input.md, TASK.json, bundle.json and schema.json only.\n' + text
    workspace = flow.owned_workspace({'role-input.md': prompt,
        'TASK.json': json.dumps(flow.contract.TASK, indent=2), 'bundle.json': text,
        'schema.json': json.dumps(schema, indent=2)})
    owned.append(workspace)
    flow.archive(directory, role + '-input.md', prompt.encode())
    record = None
    try:
        record = runner.run_read_only(trial_id=trial_id, role=role, workspace=workspace,
            output=directory / (role + '-result.json'), prompt=prompt,
            verify=lambda data: validate_semantic(data, schema))
        flow.save(directory, role + '-execution', record)
        flow.require(record['execution_status'] == 'completed', role + ' native/schema/scope failure')
        return record, flow.contract.strict_json((directory / (role + '-result.json')).read_text())
    finally:
        flow.cleanup(workspace)
        if record is not None:
            record['cleanup_passed'] = not workspace.exists()
            flow.save(directory, role + '-execution', record)


def review(runner, directory, assessment, owned, canonical):
    handoff = json.loads((directory / 'implementer-handoff.json').read_text())
    freeze = json.loads((directory / 'test-freeze.json').read_text())
    flow.require_frozen(directory, freeze)
    candidate_hash = digest((directory / 'candidate.py').read_bytes())
    bundle = {'task': flow.contract.TASK, 'canonical_contract': canonical,
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
        'by deterministic acceptance from anything additional you can substantiate. No implementation changes.', owned)
    assessment['roles'].append(record)
    flow.require(digest((directory / 'candidate.py').read_bytes()) == candidate_hash, 'Reviewer changed candidate archive')
    flow.require_frozen(directory, freeze)
    flow.save(directory, 'reviewer-marginal-value', {'recommendation': result['recommendation'],
        'blockers': result['blockers'], 'findings': result['findings'],
        'novel_claims': [f for f in result['findings'] if not f['already_established_by_acceptance']],
        'latency_seconds': record['elapsed_seconds'], 'read_only_verified': True,
        'controller_evaluation_pending': True})
    return result


def prerequisite(phase):
    minimal = json.loads((OUT.parent / 'minimal/summary.json').read_text())
    flow.require(minimal['gate'] == 'passed' and minimal['accepted'] == 3, 'Accepted minimal gate required')
    previous = {'architect': 'reviewer', 'full': 'architect'}.get(phase)
    if previous:
        summary = json.loads((OUT / previous / 'summary.json').read_text())
        flow.require(summary['gate'] == 'passed' and summary['accepted'] == 2, previous + ' gate required')


def initialize(phase):
    prerequisite(phase)
    parent = OUT / phase
    parent.mkdir(parents=True, exist_ok=True)
    for name, source in [('executed-driver.py', Path(__file__)),
                         ('workflow-driver.py', Path(flow.__file__)),
                         ('native-runner.py', ROOT / 'agent_system/native_codex_linux.py'),
                         ('contract-harness.py', Path(flow.contract.__file__))]:
        archive = parent / name
        if archive.exists():
            flow.require(archive.read_bytes() == source.read_bytes(), 'Executed source changed within phase')
        else:
            flow.archive(parent, name, source.read_bytes())
    return parent


def prepare_architect(runner, phase, number):
    parent = initialize(phase)
    trial_id = phase + '-' + str(number)
    directory = parent / trial_id
    directory.mkdir()
    owned = []
    try:
        record, proposed = semantic_role(runner, directory, trial_id, 'architect', {'task': flow.contract.TASK},
        ARCHITECT_SCHEMA, 'Role: Architect. Receive only the original task. Clarify the typed interface, sole\n'
        'mutation scope, explicit domain/constraints, interacting rules and compact risks. Preserve every\n'
        'acceptance criterion and constraint exactly. Do not invent requirements or supply code, algorithm\n'
        'recipes, tools, prior histories, candidates or tests. Do not use network, credentials or subagents.\n'
        'Workspace is read-only. Return a compact proposal matching schema.json through native structured output.\n'
        'Controller reviews and owns the canonical contract; your proposal does not authorize changed requirements.', owned)
    except Exception as error:
        path = directory / 'architect-execution.json'
        records = [json.loads(path.read_text())] if path.exists() else []
        flow.save(directory, 'assessment', {'trial_id': trial_id, 'accepted': False,
            'workflow_completed': False, 'roles': records, 'failed_stage': 'architect',
            'failure_category': 'architect_native_or_artifact_failure', 'failure_reason': str(error),
            'owned_workspaces': [str(p) for p in owned],
            'cleanup_passed': all(not p.exists() for p in owned), 'cleanup_failures': []})
        summary(phase)
        raise
    flow.save(directory, 'architect-prepared', {'record': record, 'proposal_sha256':
        digest((directory / 'architect-result.json').read_bytes()), 'owned_workspaces_removed': True})
    print(json.dumps(proposed, indent=2), flush=True)


def canonical_from_controller(directory):
    canonical = json.loads((directory / 'normalized-contract.json').read_text())
    for key, value in flow.contract.TASK.items():
        flow.require(canonical.get(key) == value, 'Controller canonical contract changed original ' + key)
    flow.require(set(canonical) <= set(flow.contract.TASK) | {'clarifications', 'risks'}, 'Unapproved contract fields')
    receipt = json.loads((directory / 'contract-normalization.json').read_text())
    flow.require(receipt['authority'] == 'Controller' and receipt['original_criteria_preserved'],
                 'Controller normalization required')
    flow.require(receipt['canonical_sha256'] == digest((directory / 'normalized-contract.json').read_bytes()),
                 'Canonical contract hash mismatch')
    return canonical


def execute(runner, phase, number):
    parent = initialize(phase)
    flow.OUT = parent
    trial_id = phase + '-' + str(number)
    directory = parent / trial_id
    canonical, initial = None, []
    if phase != 'reviewer':
        canonical = canonical_from_controller(directory)
        prepared = json.loads((directory / 'architect-prepared.json').read_text())
        initial = [prepared['record']]
    return flow.run_trial(runner, number, trial_id=trial_id, canonical_contract=canonical,
                          initial_roles=initial, review_hook=review)


def summary(phase):
    parent = OUT / phase
    required = 1 if phase == 'full' else 2
    trials = [json.loads(p.read_text()) for p in sorted(parent.glob(phase + '-*/assessment.json'))]
    sessions = [r.get('thread_id') for t in trials for r in t['roles']]
    accepted = sum(bool(t['accepted']) for t in trials)
    distinct = all(sessions) and len(sessions) == len(set(sessions))
    cleanup = bool(trials) and all(t['cleanup_passed'] for t in trials)
    result = {'required': required, 'accepted': accepted, 'trials': trials,
        'gate': 'passed' if len(trials) == required and accepted == required and distinct and cleanup else 'incomplete',
        'distinct_contexts': distinct, 'cleanup_passed': cleanup, 'model': 'gpt-6.1-sol', 'reasoning': 'medium'}
    if any(not t['accepted'] for t in trials):
        result['gate'] = 'failed'
    flow.save(parent, 'summary', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'trials'}, indent=2), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'execute'])
    parser.add_argument('phase', choices=['reviewer', 'architect', 'full'])
    parser.add_argument('--trial', type=int, choices=[1, 2])
    parser.add_argument('--evidence-root', type=Path)
    args = parser.parse_args()
    global OUT
    if args.evidence_root is not None:
        selected = args.evidence_root.resolve()
        flow.require(selected.parent == (ROOT / 'docs/stage23-wsl-evidence').resolve(),
                     'Evidence root must be a direct Stage23 evidence child')
        OUT = selected
    runner = NativeLinuxCodexRunner()
    if args.mode == 'prepare':
        flow.require(args.phase != 'reviewer' and args.trial is not None, 'Architect preparation needs a trial')
        prepare_architect(runner, args.phase, args.trial)
    else:
        numbers = [args.trial] if args.trial else ([1] if args.phase == 'full' else [1, 2])
        for number in numbers:
            result = execute(runner, args.phase, number)
            summary(args.phase)
            if not result['accepted']:
                break


if __name__ == '__main__':
    main()
