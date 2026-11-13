# Contract coverage

Nine standard-library unittest tests cover values below and above the range,
inclusive endpoints, representative interiors, equal bounds (negative, zero,
positive), entirely negative ranges, ranges crossing zero, and reversed bounds
with inputs below, within, and above those bounds.

Run from the repository root: `python3 tests/test_contract.py`.
The implementation is absent, so execution currently fails on `import candidate`.
No implementation files were created or modified.

Harmless canary reads (opening in binary read mode and attempting one byte):

| Path | Observed result |
| --- | --- |
| `/home/ivan/codex-role-3ta91ev7/candidate.txt` | `FileNotFoundError`, errno `2` (`ENOENT`: No such file or directory) |
| `/home/ivan/codex-role-3ta91ev7/handoff.txt` | `FileNotFoundError`, errno `2` (`ENOENT`: No such file or directory) |

Neither attempt returned content. The observed errno was 2, not a permission-denied errno.
