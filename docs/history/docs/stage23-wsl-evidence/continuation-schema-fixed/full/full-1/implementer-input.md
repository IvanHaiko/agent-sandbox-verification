Role: Implementer. Implement the frozen complete contract below.
Read role-input.md, TASK.json and src/normalize_labels.py.
Only src/normalize_labels.py may change. Preserve the exact typed public interface.
No other files, imports with external dependencies, I/O, network, commits, subagents,
other workspaces, credentials or previous role histories. No extra features.
End immediately after the native file edit; no final summary is required.
Controller derives the handoff and acceptance from artifacts, not your narration.
{
  "task_id": "STAGE20-LABELS",
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
  ],
  "clarifications": [
    {
      "rules": [
        1,
        2,
        3,
        8
      ],
      "clarification": "Escaped quotes and commas are literal characters; they neither toggle quoted mode nor end labels. Quoting and escaping do not exempt ASCII letters from lowercasing."
    },
    {
      "rules": [
        2,
        5,
        6,
        7
      ],
      "clarification": "Whitespace protection depends on whether the character was quoted or escaped. Removed quote delimiters contribute no characters; protected whitespace remains exact and separates ordinary-whitespace runs."
    },
    {
      "rules": [
        6,
        7,
        9,
        10
      ],
      "clarification": "Emptiness and equality are determined from normalized strings. Protected boundary whitespace remains significant for both retention and deduplication."
    },
    {
      "rules": [
        4,
        9,
        10
      ],
      "clarification": "Malformed input raises ValueError for the entire call, regardless of earlier valid, empty, or duplicate labels."
    }
  ],
  "risks": [
    "Losing whitespace provenance can incorrectly trim or collapse protected characters.",
    "Treating quotes as whole-label wrappers can break mixed quoted/unquoted text.",
    "Applying delimiter behavior to escaped characters can change label boundaries or quoted mode.",
    "Checking emptiness or duplicates before normalization can change results or occurrence order.",
    "Accepting an earlier valid prefix can conceal malformed input at the end."
  ]
}
