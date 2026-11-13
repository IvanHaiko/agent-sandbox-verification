Role: Independent Tester. Read only role-input.md, TASK.json and schema.json.
You receive the frozen task, public interface, acceptance criteria and supported domain.
No candidate, implementation stub, diff, Implementer handoff, narration or history is supplied.
Design 10-24 distinct deterministic ASCII-only cases covering ALL ten rules and their
interactions: quote concatenation, comma/quote/backslash escaping in either mode, all
six ASCII whitespace characters, ordinary versus protected boundaries and runs,
lowercasing even quoted/escaped uppercase, deduplication, empty input, protected-only
whitespace, trailing escape and unclosed quote after otherwise valid labels.
expected must be a string list, or null for whole-input ValueError. Verify expectations
against every rule. Unicode and non-string behavior are unspecified: never test them.
Write ONLY tests/test-design.json as a JSON object matching schema.json.
No executable test code, candidate access, other workspace, auth files, commits,
network, dependencies or subagents. No other file may change.
Your design is frozen and hashed before candidate exposure; Controller generates and
runs the frozen harness. End after writing the artifact; no summary is required.
{
  "task_id": "LABEL-NORMALIZATION",
  "contract_version": 1,
  "public_interface": "def normalize_labels(value: str) -> list[str]",
  "file": "src/normalize_labels.py",
  "acceptance_criteria": [
    "Scan ASCII strings left to right. An unescaped comma outside double quotes ends a label; repeated separators are allowed.",
    "An unescaped double quote toggles quoted mode anywhere within a label; quote delimiters are removed and adjacent quoted/unquoted text concatenates.",
    "Backslash escapes exactly the next character in either mode: remove the backslash, preserve the next character literally, and do not treat it as a quote or separator.",
    "A trailing unpaired backslash or unclosed double quote raises ValueError for the whole input, even after otherwise valid labels.",
    "Only ASCII whitespace (space, tab, CR, LF, vertical tab, form feed) that was neither quoted nor escaped is ordinary whitespace.",
    "Trim ordinary whitespace from each label boundary before collapsing internal ordinary-whitespace runs to one ASCII space.",
    "Quoted or escaped whitespace is protected: preserve its exact characters and multiplicity, including at label boundaries; it also breaks ordinary-whitespace runs.",
    "Lowercase ASCII A-Z in all emitted characters; preserve other non-delimiter literal characters exactly.",
    "After parsing and normalization, discard labels whose resulting string is empty. Whitespace-only protected labels are nonempty and retained.",
    "Deduplicate normalized strings by exact equality, retaining first occurrence order. Empty input returns an empty list."
  ],
  "constraints": [
    "Pure Python, standard library only, no external dependencies or I/O.",
    "ASCII string inputs are in scope; Unicode and non-string behavior are unspecified.",
    "Do not add features or mutate any file other than src/normalize_labels.py."
  ]
}
