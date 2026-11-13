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
    "design_sha256": "adcee1aa3e6818445b7f82612d1b4c25f7196f94f1ad194fcea07b61de197b6d",
    "case_count": 24,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "adcee1aa3e6818445b7f82612d1b4c25f7196f94f1ad194fcea07b61de197b6d",
    "harness_sha256": "ea8ade753efe50e65f7d5f9037c32e74cc1574d16c4f20817cac0ff3bba70303",
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
          "id": "discard_empty_and_ordinary_only",
          "input": ",,\"\", \t\r\n\u000b\f,\"\"\"\",,",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "separator_order",
          "input": ",ZETA,,Alpha,,,BETA,",
          "expected": [
            "zeta",
            "alpha",
            "beta"
          ],
          "actual": [
            "zeta",
            "alpha",
            "beta"
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
          "input": "\"A,,B\",C\",D\"E,\",\",\"\"",
          "expected": [
            "a,,b",
            "c,de",
            ","
          ],
          "actual": [
            "a,,b",
            "c,de",
            ","
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "outside_escape_kinds",
          "input": "A\\,B,C\\\"D,E\\\\F,\\G",
          "expected": [
            "a,b",
            "c\"d",
            "e\\f",
            "g"
          ],
          "actual": [
            "a,b",
            "c\"d",
            "e\\f",
            "g"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "inside_escape_kinds",
          "input": "\"A\\,B\\\"C\\\\D\\E\",F",
          "expected": [
            "a,b\"c\\de",
            "f"
          ],
          "actual": [
            "a,b\"c\\de",
            "f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_ordinary_whitespace",
          "input": " \t\r\n\u000b\fA \t\r\n\u000b\fB\f\u000b\n\r\t ",
          "expected": [
            "a b"
          ],
          "actual": [
            "a b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_quoted_whitespace",
          "input": "\"  \t\t\r\r\n\n\u000b\u000b\f\fA  \t\t\r\r\n\n\u000b\u000b\f\f\"",
          "expected": [
            "  \t\t\r\r\n\n\u000b\u000b\f\fa  \t\t\r\r\n\n\u000b\u000b\f\f"
          ],
          "actual": [
            "  \t\t\r\r\n\n\u000b\u000b\f\fa  \t\t\r\r\n\n\u000b\u000b\f\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_escaped_whitespace",
          "input": "\\ \\\t\\\r\\\n\\\u000b\\\f",
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
          "id": "mixed_boundary_protection",
          "input": " \t\" \t\"A\"\r\n\" \u000b",
          "expected": [
            " \ta\r\n"
          ],
          "actual": [
            " \ta\r\n"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_breaks_ordinary_runs",
          "input": "A \t\" \t\" \rB,A \t\\ \r B",
          "expected": [
            "a  \t b",
            "a   b"
          ],
          "actual": [
            "a  \t b",
            "a   b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_only_and_exact_dedup",
          "input": "\" \",\"  \",\"\t\r\n\u000b\f\",\\ , \t ",
          "expected": [
            " ",
            "  ",
            "\t\r\n\u000b\f"
          ],
          "actual": [
            " ",
            "  ",
            "\t\r\n\u000b\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty_quotes_do_not_split_runs",
          "input": "A \t\"\"\r B, \"\" \tC\"\"\n ",
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
          "id": "normalized_dedup_order",
          "input": " Beta ,ALPHA,bETA,\"alpha\",A \t B,a b,GAMMA,\"Be\"TA",
          "expected": [
            "beta",
            "alpha",
            "a b",
            "gamma"
          ],
          "actual": [
            "beta",
            "alpha",
            "a b",
            "gamma"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "dedup_uses_output_not_provenance",
          "input": "A B,\"A B\",A\\ B,\" A B \",A\"  \"B,a  b",
          "expected": [
            "a b",
            " a b ",
            "a  b"
          ],
          "actual": [
            "a b",
            " a b ",
            "a  b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_boundary_whitespace",
          "input": " \t\\ A\\ \r\n, \t\\  \r\\ \n",
          "expected": [
            " a ",
            "   "
          ],
          "actual": [
            " a ",
            "   "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "other_ascii_literals",
          "input": "AZ09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u001c\u007f",
          "expected": [
            "az09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u001c\u007f"
          ],
          "actual": [
            "az09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u001c\u007f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "paired_backslash_before_quote",
          "input": "A\\\\\",B\",C",
          "expected": [
            "a\\,b",
            "c"
          ],
          "actual": [
            "a\\,b",
            "c"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_quote_before_separator",
          "input": "A\\\",B",
          "expected": [
            "a\"",
            "b"
          ],
          "actual": [
            "a\"",
            "b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing_escape_outside_after_valid",
          "input": "GOOD,good,OTHER,BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing_escape_inside_after_valid",
          "input": "GOOD,OTHER,\"BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed_quote_after_valid",
          "input": "GOOD,OTHER,PRE\"BAD,TAIL",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped_quote_does_not_close",
          "input": "GOOD,\"BAD\\\"",
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
          "case": "discard_empty_and_ordinary_only",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "discard_empty_and_ordinary_only",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "separator_order",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "separator_order",
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
          "case": "outside_escape_kinds",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "outside_escape_kinds",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "inside_escape_kinds",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "inside_escape_kinds",
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
          "case": "mixed_boundary_protection",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "mixed_boundary_protection",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_breaks_ordinary_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_breaks_ordinary_runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_only_and_exact_dedup",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_only_and_exact_dedup",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "empty_quotes_do_not_split_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_quotes_do_not_split_runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "normalized_dedup_order",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "normalized_dedup_order",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "dedup_uses_output_not_provenance",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "dedup_uses_output_not_provenance",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_boundary_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_boundary_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "other_ascii_literals",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "other_ascii_literals",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "paired_backslash_before_quote",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "paired_backslash_before_quote",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_quote_before_separator",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_quote_before_separator",
          "property": "ascii_lowercase",
          "passed": true
        }
      ]
    },
    "executed_at": 1791377265.5926485,
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