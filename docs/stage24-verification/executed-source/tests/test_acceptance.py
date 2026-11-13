"""Offline guard checks for frozen acceptance; these are not live role trials."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from validation import labels_contract as contract
from agent_system.artifacts import freeze_design, require_frozen, save


def design():
    return {'task_id': contract.TASK_ID, 'contract_version': 1,
        'cases': [{'id': str(n), 'intent': 'Lowercase literal input', 'input': 'A' + str(n),
                   'expected': ['a' + str(n)]} for n in range(10)],
        'properties': ['unique_nonempty_labels', 'ascii_lowercase'],
        'rationale': 'Offline harness fixture only'}


class FrozenAcceptanceTests(unittest.TestCase):
    def test_domain_and_duplicate_ids_rejected(self):
        fixture = design()
        fixture['cases'][0]['input'] = '\u00e9'
        with self.assertRaises(ValueError):
            contract.validate_design(json.dumps(fixture).encode())
        fixture = design()
        fixture['cases'][1]['id'] = fixture['cases'][0]['id']
        with self.assertRaises(ValueError):
            contract.validate_design(json.dumps(fixture).encode())

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            contract.strict_json('{"cases": [], "cases": []}')

    def test_frozen_design_tampering_rejected(self):
        with tempfile.TemporaryDirectory(prefix='native-offline-') as temporary:
            directory = Path(temporary)
            save(directory, 'frozen-task', contract.TASK)
            freeze, _, _ = freeze_design(directory, json.dumps(design()).encode(), contract)
            require_frozen(directory, freeze)
            (directory / 'frozen-test-design.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'Frozen test design changed'):
                require_frozen(directory, freeze)

    def test_harness_rejects_incorrect_candidate(self):
        with tempfile.TemporaryDirectory(prefix='native-offline-') as temporary:
            directory = Path(temporary)
            (directory / 'src').mkdir()
            source = directory / contract.TASK['file']
            source.write_text('def normalize_labels(value: str) -> list[str]:\n    return []\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', contract.acceptance_source(design())],
                cwd=directory, capture_output=True, text=True, timeout=10)
            receipt = json.loads(result.stdout)
            self.assertEqual(result.returncode, 1)
            self.assertFalse(receipt['passed'])
            self.assertTrue(receipt['interface'])
            self.assertTrue(all(not case['passed'] for case in receipt['cases']))

    def test_value_error_expectation_is_not_any_exception(self):
        fixture = design()
        fixture['cases'][0]['expected'] = None
        with tempfile.TemporaryDirectory(prefix='native-offline-') as temporary:
            directory = Path(temporary)
            (directory / 'src').mkdir()
            (directory / contract.TASK['file']).write_text(
                'def normalize_labels(value: str) -> list[str]:\n    raise RuntimeError()\n')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', contract.acceptance_source(fixture)],
                cwd=directory, capture_output=True, text=True, timeout=10)
            receipt = json.loads(result.stdout)
            self.assertFalse(receipt['cases'][0]['passed'])
            self.assertEqual(receipt['cases'][0]['error'], 'RuntimeError')


if __name__ == '__main__':
    unittest.main()
