"""One bounded integration fixture for the current native workflow; no historical gates."""
import argparse
import json
from pathlib import Path

from agent_system.artifacts import digest, require, save
from agent_system.controller import run_workflow
from agent_system.native_codex_linux import NativeLinuxCodexRunner
from agent_system.roles import architect_schema, load_canonical, review, semantic_role
from . import labels_contract as contract


ARCHITECT_INSTRUCTION = (
    'Role: Architect. Receive only the original task. Clarify the typed interface, sole\n'
    'mutation scope, explicit domain/constraints, interacting rules and compact risks. Preserve every\n'
    'acceptance criterion and constraint exactly. Do not invent requirements or supply code, algorithm\n'
    'recipes, tools, prior histories, candidates or tests. Do not use network, credentials or subagents.\n'
    'Workspace is read-only. Return a compact proposal matching schema.json through native structured output.\n'
    'Controller reviews and owns the canonical contract; your proposal does not authorize changed requirements.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['minimal', 'prepare-full', 'full'])
    parser.add_argument('--evidence', required=True, type=Path)
    args = parser.parse_args()
    directory = args.evidence.resolve()
    directory.parent.mkdir(parents=True, exist_ok=True)
    runner = NativeLinuxCodexRunner()
    if args.mode == 'prepare-full':
        directory.mkdir()
        save(directory, 'frozen-task', contract.TASK)
        owned = []
        try:
            record, _ = semantic_role(runner, directory, directory.name, 'architect',
                {'task': contract.TASK}, architect_schema(contract), ARCHITECT_INSTRUCTION, owned, contract)
            save(directory, 'architect-prepared', {'record': record,
                'proposal_sha256': digest((directory / 'architect-result.json').read_bytes()),
                'owned_workspaces_removed': all(not p.exists() for p in owned)})
        except Exception as error:
            execution = directory / 'architect-execution.json'
            save(directory, 'assessment', {'accepted': False, 'failed_stage': 'architect',
                'failure_reason': str(error), 'roles': [json.loads(execution.read_text())] if execution.exists() else [],
                'cleanup_passed': all(not p.exists() for p in owned),
                'owned_workspaces': [str(p) for p in owned]})
            raise
        print('Architect proposal ready for Controller normalization in ' + str(directory), flush=True)
        return 0
    canonical, initial = None, []
    if args.mode == 'full':
        canonical = load_canonical(directory, contract)
        prepared = json.loads((directory / 'architect-prepared.json').read_text())
        require(prepared['proposal_sha256'] == digest((directory / 'architect-result.json').read_bytes()),
                'Architect proposal changed after preparation')
        initial = [prepared['record']]
    result = run_workflow(runner, directory, contract, canonical_contract=canonical,
        initial_roles=initial, review_hook=review if args.mode == 'full' else None)
    return 0 if result['accepted'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
