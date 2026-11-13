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
    ],
    "clarifications": [
      {
        "rules": [
          1,
          2,
          3,
          8
        ],
        "clarification": "Escaped quotes and commas are literal characters and have no delimiter effect. Escaped ASCII uppercase letters still become lowercase."
      },
      {
        "rules": [
          2,
          5,
          6,
          7
        ],
        "clarification": "Whitespace protection depends on quoting or escaping. Removed quote delimiters do not themselves protect adjacent unquoted whitespace or break ordinary-whitespace runs."
      },
      {
        "rules": [
          6,
          7,
          9,
          10
        ],
        "clarification": "Protected boundary whitespace remains part of the normalized string, makes a whitespace-only label nonempty, and participates in exact-equality deduplication."
      },
      {
        "rules": [
          4,
          9,
          10
        ],
        "clarification": "Malformed input raises ValueError for the whole call regardless of earlier valid, empty, or duplicate labels."
      }
    ],
    "risks": [
      "Treating escaped delimiters as syntax can change label boundaries or quoted mode.",
      "Losing whitespace protection can incorrectly trim, collapse, or discard labels.",
      "Applying literal preservation without ASCII lowercasing can produce incorrect normalized strings.",
      "Deduplicating before normalization can retain equivalent labels or lose first-occurrence order.",
      "Accepting earlier labels despite malformed trailing input violates whole-input validation."
    ]
  },
  "candidate_diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_space = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_space = False\n+            continue\n+        elif character in whitespace and not quoted:\n+            pending_space = bool(characters)\n+            continue\n+\n+        # Defer ordinary whitespace until a literal follows, trimming the\n+        # boundaries while preserving quoted and escaped whitespace exactly.\n+        if pending_space:\n+            characters.append(\" \")\n+            pending_space = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
  "implementation_handoff": {
    "role": "implementer",
    "execution_status": "completed",
    "model": "gpt-6.1-sol",
    "changed_files": [
      "src/normalize_labels.py"
    ],
    "candidate_hashes": {
      "src/normalize_labels.py": "3c04f9e7e520e459a6feb63bea4502974bb6d446b72e1437db3f99b23a2aaf1c"
    },
    "diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_space = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_space = False\n+            continue\n+        elif character in whitespace and not quoted:\n+            pending_space = bool(characters)\n+            continue\n+\n+        # Defer ordinary whitespace until a literal follows, trimming the\n+        # boundaries while preserving quoted and escaped whitespace exactly.\n+        if pending_space:\n+            characters.append(\" \")\n+            pending_space = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
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
    "design_sha256": "27d90045b5cd79a3d809e4d9bd4d66d74ce1e1bf5a06f9ca06458b41ffcf1894",
    "case_count": 22,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "27d90045b5cd79a3d809e4d9bd4d66d74ce1e1bf5a06f9ca06458b41ffcf1894",
    "harness_sha256": "57bcb3e86b6786ba521fc8c0057d562f591eb4192dbd095a69d4cacdfff9a053",
    "candidate_sha256_before": "3c04f9e7e520e459a6feb63bea4502974bb6d446b72e1437db3f99b23a2aaf1c",
    "candidate_sha256_after": "3c04f9e7e520e459a6feb63bea4502974bb6d446b72e1437db3f99b23a2aaf1c",
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
          "id": "empty_labels_and_ordinary_whitespace",
          "input": ",, \t\r\n\u000b\f,\"\", ,",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "separator_order_and_case",
          "input": ",Beta,, ALPHA ,beta,GAMMA,alpha,",
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
          "id": "quote_concatenation_anywhere",
          "input": "AB\"CD\"EF\"GH\"I,\"ABC\"DEFGHI,A\"\"BCDEFGHI",
          "expected": [
            "abcdefghi"
          ],
          "actual": [
            "abcdefghi"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted_commas",
          "input": "PRE\"A,B\"POST,\",\",\"X,,Y\",END",
          "expected": [
            "prea,bpost",
            ",",
            "x,,y",
            "end"
          ],
          "actual": [
            "prea,bpost",
            ",",
            "x,,y",
            "end"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escapes_outside_quotes",
          "input": "A\\,B,C\\\"D,E\\\\F,\\Z",
          "expected": [
            "a,b",
            "c\"d",
            "e\\f",
            "z"
          ],
          "actual": [
            "a,b",
            "c\"d",
            "e\\f",
            "z"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escapes_inside_quotes",
          "input": "\"A\\,B\\\"C\\\\D\\Z\",NEXT",
          "expected": [
            "a,b\"c\\dz",
            "next"
          ],
          "actual": [
            "a,b\"c\\dz",
            "next"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_ordinary_whitespace",
          "input": " \t\r\n\u000b\fA \t\r\n\u000b\f B\f\u000b\n\r\t ",
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
          "id": "all_quoted_whitespace_only",
          "input": "\"  \t\t\r\r\n\n\u000b\u000b\f\f\"",
          "expected": [
            "  \t\t\r\r\n\n\u000b\u000b\f\f"
          ],
          "actual": [
            "  \t\t\r\r\n\n\u000b\u000b\f\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_escaped_whitespace_only",
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
          "input": " \t\"  A\t \" \r, \n\\ B\\ \t",
          "expected": [
            "  a\t ",
            " b "
          ],
          "actual": [
            "  a\t ",
            " b "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted_whitespace_breaks_runs",
          "input": "A \t\"\t  \" \rB",
          "expected": [
            "a \t   b"
          ],
          "actual": [
            "a \t   b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_whitespace_breaks_runs",
          "input": "A  \\\t \r\nB",
          "expected": [
            "a \t b"
          ],
          "actual": [
            "a \t b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty_quotes_do_not_break_runs",
          "input": " \"\" \tA \"\" \tB \"\" , \"\" \t",
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
          "id": "deduplicate_after_normalization",
          "input": " Z ,A  B,a\tb,\"A\" B,\\A B,z,C,A B",
          "expected": [
            "z",
            "a b",
            "c"
          ],
          "actual": [
            "z",
            "a b",
            "c"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_equality_and_order",
          "input": "\" \",\\ ,\"  \",\\ \\ , ,\"\t\",\\\t,\" A\",A,\"A \",\" A\"",
          "expected": [
            " ",
            "  ",
            "\t",
            " a",
            "a",
            "a "
          ],
          "actual": [
            " ",
            "  ",
            "\t",
            " a",
            "a",
            "a "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "other_ascii_literals",
          "input": "AZ09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u0007\u001b\u007f,\\Q\\!",
          "expected": [
            "az09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u0007\u001b\u007f",
            "q!"
          ],
          "actual": [
            "az09!#$%&'()*+-./:;<=>?@[]^_`{|}~\u0000\u0007\u001b\u007f",
            "q!"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_backslash_leaves_next_syntax_active",
          "input": "A\\\\,B\\\\\"C,D\",E",
          "expected": [
            "a\\",
            "b\\c,d",
            "e"
          ],
          "actual": [
            "a\\",
            "b\\c,d",
            "e"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing_escape_after_valid_and_empty_labels",
          "input": "GOOD,good,,\"\",BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing_escape_in_quotes",
          "input": "GOOD,\"BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed_quote_after_valid_and_duplicate_labels",
          "input": "GOOD,,good,\"\",BAD\"MORE,STILL",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped_quote_does_not_close_quote",
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
          "case": "empty_labels_and_ordinary_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_labels_and_ordinary_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "separator_order_and_case",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "separator_order_and_case",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quote_concatenation_anywhere",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quote_concatenation_anywhere",
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
          "case": "all_quoted_whitespace_only",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all_quoted_whitespace_only",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all_escaped_whitespace_only",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all_escaped_whitespace_only",
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
          "case": "quoted_whitespace_breaks_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quoted_whitespace_breaks_runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_whitespace_breaks_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_whitespace_breaks_runs",
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
          "case": "deduplicate_after_normalization",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "deduplicate_after_normalization",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_equality_and_order",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_equality_and_order",
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
          "case": "escaped_backslash_leaves_next_syntax_active",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_backslash_leaves_next_syntax_active",
          "property": "ascii_lowercase",
          "passed": true
        }
      ]
    },
    "executed_at": 1791381494.3736835,
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