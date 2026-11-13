Role: Reviewer. Review only the supplied contract, diff and Controller artifact evidence.
You have no prior role conversation or hidden implementation context. Your entire workspace is read-only.
Do not modify implementation, tests or inputs, run acceptance again, read other workspaces, use network,
credentials or subagents. Return only JSON matching schema.json through native structured output.
Recommend accept/reject/request-fix. Identify concrete in-scope defects, missing evidence or contract
risks; do not invent requirements. Report blockers and findings, distinguishing facts already established
by deterministic acceptance from anything additional you can substantiate. No implementation changes.
Read role-input.md, TASK.json, bundle.json and schema.json only.
{
  "task": {
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
    ]
  },
  "canonical_contract": {
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
    ]
  },
  "candidate_diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,45 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_space = False\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_space = False\n+            continue\n+        elif character in \" \\t\\r\\n\\v\\f\" and not quoted:\n+            pending_space = bool(characters)\n+            continue\n+\n+        if pending_space:\n+            characters.append(\" \")\n+            pending_space = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
  "implementation_handoff": {
    "role": "implementer",
    "execution_status": "completed",
    "model": "gpt-6.1-sol",
    "changed_files": [
      "src/normalize_labels.py"
    ],
    "candidate_hashes": {
      "src/normalize_labels.py": "341037fe750c3613cde3e1ed429ca8b7834a1b38c7b817e3aa6b825f8807bf27"
    },
    "diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,45 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_space = False\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_space = False\n+            continue\n+        elif character in \" \\t\\r\\n\\v\\f\" and not quoted:\n+            pending_space = bool(characters)\n+            continue\n+\n+        if pending_space:\n+            characters.append(\" \")\n+            pending_space = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
    "mutation_scope_valid": true,
    "interface_check": {
      "valid": true,
      "public_interface_verified": true,
      "syntax_verified": true
    },
    "candidate_status": "unaccepted",
    "accepted": false,
    "authority": "controller_observed_artifacts"
  },
  "frozen_test_summary": {
    "design_sha256": "84ce3f0ffbde1167fc645cbad1caebeaa4130dd031c2e8a4529eb56b35e340bd",
    "case_count": 22,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "84ce3f0ffbde1167fc645cbad1caebeaa4130dd031c2e8a4529eb56b35e340bd",
    "harness_sha256": "90a7e399ff7b7adb152cc47151d07483901ee08b66e52865d3f8c4fba2e1599f",
    "candidate_sha256_before": "341037fe750c3613cde3e1ed429ca8b7834a1b38c7b817e3aa6b825f8807bf27",
    "candidate_sha256_after": "341037fe750c3613cde3e1ed429ca8b7834a1b38c7b817e3aa6b825f8807bf27",
    "mutation_scope_valid": true,
    "result": {
      "passed": true,
      "interface": true,
      "cases": [
        {
          "id": "empty_input",
          "input": "",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "discard_empty_labels",
          "input": ",, \t\r\n\u000b\f,\"\", \"\" ,,,",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "separators_and_order",
          "input": ",BETA,,Alpha,BETA,,,GAMMA,alpha,",
          "expected": [
            "beta",
            "alpha",
            "gamma"
          ],
          "actual": [
            "beta",
            "alpha",
            "gamma"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quote_concatenation",
          "input": "PRE\"MiD\"POST,\"A\"B\"C\",X\"\"Y,\"\"Z\"\"",
          "expected": [
            "premidpost",
            "abc",
            "xy",
            "z"
          ],
          "actual": [
            "premidpost",
            "abc",
            "xy",
            "z"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted_commas",
          "input": "\",A,,B,\",C\",D\"E,F",
          "expected": [
            ",a,,b,",
            "c,de",
            "f"
          ],
          "actual": [
            ",a,,b,",
            "c,de",
            "f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escapes_outside_quotes",
          "input": "A\\,B,C\\\"D,E\\\\F",
          "expected": [
            "a,b",
            "c\"d",
            "e\\f"
          ],
          "actual": [
            "a,b",
            "c\"d",
            "e\\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escapes_inside_quotes",
          "input": "\"A\\,B\\\"C\\\\D,E\",F",
          "expected": [
            "a,b\"c\\d,e",
            "f"
          ],
          "actual": [
            "a,b\"c\\d,e",
            "f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_ordinary_whitespace",
          "input": " \t\r\n\u000b\fA \t\r\n\u000b\fB\f\u000b\n\r\t , C\tD\rE\nF\u000bG\fH ",
          "expected": [
            "a b",
            "c d e f g h"
          ],
          "actual": [
            "a b",
            "c d e f g h"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_quoted_whitespace",
          "input": "\" \t\r\n\u000b\f \t\r\n\u000b\f\"",
          "expected": [
            " \t\r\n\u000b\f \t\r\n\u000b\f"
          ],
          "actual": [
            " \t\r\n\u000b\f \t\r\n\u000b\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_escaped_whitespace",
          "input": " \t\\ \\\t\\\r\\\n\\\u000b\\\f \r",
          "expected": [
            " \t\r\n\u000b\f"
          ],
          "actual": [
            " \t\r\n\u000b\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_boundaries",
          "input": " \r\" \tA\t \"\n , \t\\ B\\ \r ",
          "expected": [
            " \ta\t ",
            " b "
          ],
          "actual": [
            " \ta\t ",
            " b "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_breaks_runs",
          "input": "A \t\"\t\" \r\nB,A  \\   B,A \"  \" B",
          "expected": [
            "a \t b",
            "a   b",
            "a    b"
          ],
          "actual": [
            "a \t b",
            "a   b",
            "a    b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty_quotes_do_not_break_runs",
          "input": "A \t\"\"\r\n B, \"\" \tC\"\"\r ",
          "expected": [
            "a b",
            "c"
          ],
          "actual": [
            "a b",
            "c"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "normalization_before_deduplication",
          "input": " BETA ,A  B,\"a b\",a\tB,be\"TA\",\\BETA,ALPHA,alpha",
          "expected": [
            "beta",
            "a b",
            "alpha"
          ],
          "actual": [
            "beta",
            "a b",
            "alpha"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_equality_and_distinctions",
          "input": "A B,\"A B\",A\\ B,\"A  B\",\"A\tB\",A\tB,\" \",\\ ,\"  \",\"\t\"",
          "expected": [
            "a b",
            "a  b",
            "a\tb",
            " ",
            "  ",
            "\t"
          ],
          "actual": [
            "a b",
            "a  b",
            "a\tb",
            " ",
            "  ",
            "\t"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "literal_ascii_and_escape_next_only",
          "input": "\\N\\T\\R,\"\\A\\Z\",!@#$%^&*()_+-=[]{};:'/?<>.|`~0129,\u0000\u001b\u007f",
          "expected": [
            "ntr",
            "az",
            "!@#$%^&*()_+-=[]{};:'/?<>.|`~0129",
            "\u0000\u001b\u007f"
          ],
          "actual": [
            "ntr",
            "az",
            "!@#$%^&*()_+-=[]{};:'/?<>.|`~0129",
            "\u0000\u001b\u007f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "paired_backslash_before_delimiter",
          "input": "A\\\\,B,C\\\\\"D,E\"",
          "expected": [
            "a\\",
            "b",
            "c\\d,e"
          ],
          "actual": [
            "a\\",
            "b",
            "c\\d,e"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_quote_and_later_toggle",
          "input": "A\\\"\"B,C\"D,\"E\\\"F\"G",
          "expected": [
            "a\"b,cd",
            "e\"fg"
          ],
          "actual": [
            "a\"b,cd",
            "e\"fg"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing_escape_after_valid_labels",
          "input": "GOOD,good,OK,TAIL\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed_quote_after_valid_labels",
          "input": "GOOD,OK,PRE\"TAIL,STILL",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing_escape_in_quote",
          "input": "GOOD,\"TAIL\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped_final_quote_does_not_close",
          "input": "GOOD,\"TAIL\\\"",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        }
      ],
      "properties": [
        {
          "case": "empty_input",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_input",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "discard_empty_labels",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "discard_empty_labels",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "separators_and_order",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "separators_and_order",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quote_concatenation",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quote_concatenation",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quoted_commas",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quoted_commas",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escapes_outside_quotes",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escapes_outside_quotes",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escapes_inside_quotes",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escapes_inside_quotes",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all_ordinary_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all_ordinary_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all_quoted_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all_quoted_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all_escaped_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all_escaped_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_boundaries",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_boundaries",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_breaks_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_breaks_runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "empty_quotes_do_not_break_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_quotes_do_not_break_runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "normalization_before_deduplication",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "normalization_before_deduplication",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_equality_and_distinctions",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_equality_and_distinctions",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "literal_ascii_and_escape_next_only",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "literal_ascii_and_escape_next_only",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "paired_backslash_before_delimiter",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "paired_backslash_before_delimiter",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_quote_and_later_toggle",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_quote_and_later_toggle",
          "property": "ascii_lowercase",
          "passed": true
        }
      ]
    },
    "executed_at": 1791377408.7817247,
    "sandbox": "native Linux Codex; read-only workspace; no project network"
  },
  "scope_interface_evidence": {
    "implementation_scope_valid": true,
    "interface": {
      "valid": true,
      "public_interface_verified": true,
      "syntax_verified": true
    }
  }
}