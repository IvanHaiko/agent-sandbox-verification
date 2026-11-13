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
  },
  "candidate_diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,50 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        nonlocal pending_whitespace\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+        pending_whitespace = False\n+\n+    for character in value:\n+        protected = quoted or escaped\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            continue\n+\n+        if character in whitespace and not protected:\n+            pending_whitespace = True\n+            continue\n+\n+        if pending_whitespace:\n+            if characters:\n+                characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
  "implementation_handoff": {
    "role": "implementer",
    "execution_status": "completed",
    "model": "gpt-6.1-sol",
    "changed_files": [
      "src/normalize_labels.py"
    ],
    "candidate_hashes": {
      "src/normalize_labels.py": "e1f416b51aca5c0af13f8e1e054463b124bf77a42188dafedb2b4d8196cf1809"
    },
    "diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,50 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        nonlocal pending_whitespace\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+        pending_whitespace = False\n+\n+    for character in value:\n+        protected = quoted or escaped\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            continue\n+\n+        if character in whitespace and not protected:\n+            pending_whitespace = True\n+            continue\n+\n+        if pending_whitespace:\n+            if characters:\n+                characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
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
    "design_sha256": "d2e0a667124e2a7da3a4d5b4f552f1774f2dfad680522e48259dd7a80c0d22c7",
    "case_count": 24,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "d2e0a667124e2a7da3a4d5b4f552f1774f2dfad680522e48259dd7a80c0d22c7",
    "harness_sha256": "a00968b84f17f2e412d517d97b6730609fd09e4c76ab4ac817fcfbad3d82c469",
    "candidate_sha256_before": "e1f416b51aca5c0af13f8e1e054463b124bf77a42188dafedb2b4d8196cf1809",
    "candidate_sha256_after": "e1f416b51aca5c0af13f8e1e054463b124bf77a42188dafedb2b4d8196cf1809",
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
          "id": "empty_labels_and_separators",
          "input": ",,, \t\r\n\u000b\f,\"\",,\"\"\"\",",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "basic_order_and_case",
          "input": ", ZEBRA ,, Apple ,zebra,BANANA,apple,",
          "expected": [
            "zebra",
            "apple",
            "banana"
          ],
          "actual": [
            "zebra",
            "apple",
            "banana"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quotes_concatenate_anywhere",
          "input": "AB\"CD\"EF,\"A\"B\"C\"D,ab\"\"cd,\"\"X\"\"Y\"\"",
          "expected": [
            "abcdef",
            "abcd",
            "xy"
          ],
          "actual": [
            "abcdef",
            "abcd",
            "xy"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted_commas",
          "input": "A\"B,C\"D,\",\",\"X,Y\",Z",
          "expected": [
            "ab,cd",
            ",",
            "x,y",
            "z"
          ],
          "actual": [
            "ab,cd",
            ",",
            "x,y",
            "z"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escapes_outside_quotes",
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
          "id": "escapes_inside_quotes",
          "input": "\"A\\,B\\\"C\\\\D\\E\",TAIL",
          "expected": [
            "a,b\"c\\de",
            "tail"
          ],
          "actual": [
            "a,b\"c\\de",
            "tail"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escape_is_not_c_style",
          "input": "X\\nY,X\\tY,\"X\\rY\",\\Q\\R",
          "expected": [
            "xny",
            "xty",
            "xry",
            "qr"
          ],
          "actual": [
            "xny",
            "xty",
            "xry",
            "qr"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_ordinary_whitespace",
          "input": " \t\r\n\u000b\fA \t\r\n\u000b\fB\f\u000b\n\r\t , C\t\tD ",
          "expected": [
            "a b",
            "c d"
          ],
          "actual": [
            "a b",
            "c d"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_quoted_whitespace",
          "input": "\" \t\r\n\u000b\fA  \t\t\r\r\n\n\u000b\u000b\f\fB \t\r\n\u000b\f\"",
          "expected": [
            " \t\r\n\u000b\fa  \t\t\r\r\n\n\u000b\u000b\f\fb \t\r\n\u000b\f"
          ],
          "actual": [
            " \t\r\n\u000b\fa  \t\t\r\r\n\n\u000b\u000b\f\fb \t\r\n\u000b\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_escaped_whitespace",
          "input": "\\ \\\t\\\r\\\n\\\u000b\\\fA\\ \\\t\\\r\\\n\\\u000b\\\f",
          "expected": [
            " \t\r\n\u000b\fa \t\r\n\u000b\f"
          ],
          "actual": [
            " \t\r\n\u000b\fa \t\r\n\u000b\f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_only_whitespace",
          "input": "\" \t\r\n\u000b\f\",\\ \\\t\\\r\\\n\\\u000b\\\f,\"  \",\\ \\ ,\"\", \t\r\n\u000b\f",
          "expected": [
            " \t\r\n\u000b\f",
            "  "
          ],
          "actual": [
            " \t\r\n\u000b\f",
            "  "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "ordinary_trim_around_protected_boundaries",
          "input": " \t\"  A \t\" \r , \n\\ B\\ \t",
          "expected": [
            "  a \t",
            " b "
          ],
          "actual": [
            "  a \t",
            " b "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_whitespace_breaks_runs",
          "input": "A \t\" \t \"\r\n B",
          "expected": [
            "a  \t  b"
          ],
          "actual": [
            "a  \t  b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty_quotes_do_not_break_runs",
          "input": " \t\"\"A \t\"\"\r\n B\"\" \f",
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
          "id": "ordinary_whitespace_inside_protected_edges",
          "input": "\" \" \tA \t\" \"",
          "expected": [
            "  a  "
          ],
          "actual": [
            "  a  "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "deduplicate_after_normalization",
          "input": " B, a,A,b,\"A\",\\A,C,c ,a ",
          "expected": [
            "b",
            "a",
            "c"
          ],
          "actual": [
            "b",
            "a",
            "c"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_boundaries_affect_equality",
          "input": "A,\" A\",A\\ ,\"A \",\"A\",\\ A,\" A \"",
          "expected": [
            "a",
            " a",
            "a ",
            " a "
          ],
          "actual": [
            "a",
            " a",
            "a ",
            " a "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "equality_ignores_provenance_after_normalization",
          "input": "A B,A\tB,\"A B\",A\\ B,\"A  B\",A\\ \\ B",
          "expected": [
            "a b",
            "a  b"
          ],
          "actual": [
            "a b",
            "a  b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "other_ascii_literals",
          "input": "FOO;BAR:42/BAZ_[X]{Y}!@#$%^&*()-+=.?'<>",
          "expected": [
            "foo;bar:42/baz_[x]{y}!@#$%^&*()-+=.?'<>"
          ],
          "actual": [
            "foo;bar:42/baz_[x]{y}!@#$%^&*()-+=.?'<>"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing_escape_outside_after_valid_prefix",
          "input": "OK,,ok,\"\",NEXT\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing_escape_inside_after_valid_prefix",
          "input": "OK,\"NEXT\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed_midlabel_quote_after_valid_prefix",
          "input": "OK,,ok,\"\",PRE\"NEXT",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped_final_quote_does_not_close",
          "input": "OK,\"BAD\\\"",
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
          "case": "empty_labels_and_separators",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_labels_and_separators",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "basic_order_and_case",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "basic_order_and_case",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quotes_concatenate_anywhere",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quotes_concatenate_anywhere",
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
          "case": "escape_is_not_c_style",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escape_is_not_c_style",
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
          "case": "protected_only_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_only_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "ordinary_trim_around_protected_boundaries",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "ordinary_trim_around_protected_boundaries",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected_whitespace_breaks_runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_whitespace_breaks_runs",
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
          "case": "ordinary_whitespace_inside_protected_edges",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "ordinary_whitespace_inside_protected_edges",
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
          "case": "protected_boundaries_affect_equality",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected_boundaries_affect_equality",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "equality_ignores_provenance_after_normalization",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "equality_ignores_provenance_after_normalization",
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
        }
      ]
    },
    "executed_at": 1791381740.7577012,
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