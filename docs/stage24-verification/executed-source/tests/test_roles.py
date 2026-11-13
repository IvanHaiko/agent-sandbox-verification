"""Guard the two new semantic role boundaries; no live inference."""
import copy
import json
import unittest

import jsonschema
from agent_system import roles as continuation
from validation import labels_contract as contract
from agent_system.native_codex_linux import native_errors


class SemanticGuards(unittest.TestCase):
    def test_multiline_native_error_is_recoverable_without_other_fields(self):
        output = 'ERROR: {\n"error": {"message": "Invalid schema", "code": "invalid_json_schema",\n'
        output += '"internal_payload": "must not be retained"}\n}\nPrivate reasoning\n'
        errors = native_errors(output)
        self.assertEqual(len(errors), 1)
        self.assertIn('Invalid schema', errors[0])
        self.assertIn('invalid_json_schema', errors[0])
        self.assertNotIn('internal_payload', errors[0])
        self.assertNotIn('Private reasoning', errors[0])

    def test_error_diagnostics_exclude_role_prose_and_redact_secrets(self):
        output = 'thinking\nPrivate reasoning\nERROR: Invalid schema\nError: Bearer abc123 sk-testsecret\n'
        errors = native_errors(output)
        self.assertEqual(errors[0], 'ERROR: Invalid schema')
        self.assertEqual(errors[1], 'Error: Bearer <redacted> <redacted>')
        self.assertNotIn('Private reasoning', '\n'.join(errors))

    def test_review_cannot_accept_with_blockers(self):
        value = {'recommendation': 'accept', 'blockers': ['Contract defect'],
                 'findings': [], 'rationale': 'Contradictory recommendation'}
        with self.assertRaisesRegex(RuntimeError, 'contradicts blockers'):
            continuation.validate_semantic(json.dumps(value).encode(), continuation.REVIEW_SCHEMA, contract)

    def test_architect_cannot_change_original_acceptance_or_scope(self):
        task = contract.TASK
        value = {'public_interface': task['public_interface'], 'allowed_mutation_scope': [task['file']],
            'acceptance_criteria': task['acceptance_criteria'], 'constraints': task['constraints'],
            'clarifications': [], 'risks': []}
        self.assertTrue(continuation.validate_semantic(json.dumps(value).encode(),
                                                     continuation.architect_schema(contract), contract)['valid'])
        changed = copy.deepcopy(value)
        changed['allowed_mutation_scope'].append('src/other.py')
        with self.assertRaises(jsonschema.ValidationError):
            continuation.validate_semantic(json.dumps(changed).encode(), continuation.architect_schema(contract), contract)
        changed = copy.deepcopy(value)
        changed['acceptance_criteria'][0] = 'Accept Unicode'
        with self.assertRaises(jsonschema.ValidationError):
            continuation.validate_semantic(json.dumps(changed).encode(), continuation.architect_schema(contract), contract)
        changed = copy.deepcopy(value)
        changed['acceptance_criteria'] = list(reversed(changed['acceptance_criteria']))
        with self.assertRaisesRegex(RuntimeError, 'changed original acceptance_criteria'):
            continuation.validate_semantic(json.dumps(changed).encode(), continuation.architect_schema(contract), contract)
        changed = copy.deepcopy(value)
        changed['acceptance_criteria'][1] = changed['acceptance_criteria'][0]
        with self.assertRaisesRegex(RuntimeError, 'changed original acceptance_criteria'):
            continuation.validate_semantic(json.dumps(changed).encode(), continuation.architect_schema(contract), contract)


if __name__ == '__main__':
    unittest.main()
