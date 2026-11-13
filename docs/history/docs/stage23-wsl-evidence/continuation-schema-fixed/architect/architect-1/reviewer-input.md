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
          4
        ],
        "clarification": "Escaped commas remain literal in either mode; escaped quotes do not toggle mode. Any trailing unpaired backslash or unclosed quote invalidates the entire input, including preceding valid labels."
      },
      {
        "rules": [
          2,
          5,
          6,
          7
        ],
        "clarification": "Whitespace treatment depends on whether each character was quoted or escaped, even after quote delimiters are removed. Protected whitespace remains exact and interrupts ordinary-whitespace runs; only ordinary whitespace at label boundaries is trimmed."
      },
      {
        "rules": [
          3,
          7,
          8
        ],
        "clarification": "Quote and escape protection preserves whitespace and prevents delimiter interpretation; it does not exempt emitted ASCII A-Z from lowercasing."
      },
      {
        "rules": [
          6,
          7,
          9,
          10
        ],
        "clarification": "Emptiness and duplicate equality concern the final normalized strings. Protected whitespace alone constitutes a retained label, and equal normalized labels retain only their first occurrence."
      }
    ],
    "risks": [
      "Losing whitespace provenance can incorrectly trim or collapse protected characters.",
      "Treating escaped delimiters as syntax can change label boundaries or quote state.",
      "Returning preceding labels despite a malformed suffix violates whole-input failure.",
      "Deduplicating before normalization or ignoring protected whitespace can change results or first-occurrence order."
    ]
  },
  "candidate_diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    ascii_whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_whitespace = False\n+            continue\n+        elif character in ascii_whitespace and not quoted:\n+            pending_whitespace = bool(characters)\n+            continue\n+\n+        # Defer ordinary whitespace so boundary runs are discarded, while\n+        # each protected character is emitted exactly and ends any such run.\n+        if pending_whitespace:\n+            characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
  "implementation_handoff": {
    "role": "implementer",
    "execution_status": "completed",
    "model": "gpt-6.1-sol",
    "changed_files": [
      "src/normalize_labels.py"
    ],
    "candidate_hashes": {
      "src/normalize_labels.py": "b2451a1dfcdf5f59e3abcdb1f09223b936464836d4b5f185adbdf5e019e851c2"
    },
    "diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    ascii_whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_whitespace = False\n+            continue\n+        elif character in ascii_whitespace and not quoted:\n+            pending_whitespace = bool(characters)\n+            continue\n+\n+        # Defer ordinary whitespace so boundary runs are discarded, while\n+        # each protected character is emitted exactly and ends any such run.\n+        if pending_whitespace:\n+            characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
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
    "design_sha256": "4126e0333e3b27ae6a6b3028fef97b84d4e49fafbc6ab4f620484b05852b7200",
    "case_count": 23,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "4126e0333e3b27ae6a6b3028fef97b84d4e49fafbc6ab4f620484b05852b7200",
    "harness_sha256": "0806554c34466db9a9acd462b6f32ddfb961ec2064c5d3e2693d9b3dd5e55f5e",
    "candidate_sha256_before": "b2451a1dfcdf5f59e3abcdb1f09223b936464836d4b5f185adbdf5e019e851c2",
    "candidate_sha256_after": "b2451a1dfcdf5f59e3abcdb1f09223b936464836d4b5f185adbdf5e019e851c2",
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
          "id": "empty_segments",
          "input": ",, \t\r\n\u000b\f,\"\", \"\" ,,,",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "order_and_ascii_case",
          "input": ",ZETA,,Alpha,BETA,zeta,ALPHA,,Gamma,",
          "expected": [
            "zeta",
            "alpha",
            "beta",
            "gamma"
          ],
          "actual": [
            "zeta",
            "alpha",
            "beta",
            "gamma"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quote_concatenation",
          "input": "AB\"CD\"EF\"GH\",\"AB\"CD\"EF\"GH,A\"\"B,\"\"X\"\"",
          "expected": [
            "abcdefgh",
            "ab",
            "x"
          ],
          "actual": [
            "abcdefgh",
            "ab",
            "x"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted_commas",
          "input": "A\"B,C\"D,\"E,,F\",\",\",G",
          "expected": [
            "ab,cd",
            "e,,f",
            ",",
            "g"
          ],
          "actual": [
            "ab,cd",
            "e,,f",
            ",",
            "g"
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
          "id": "all_ordinary_whitespace",
          "input": " \t\r\n\u000b\fA \t\r\n\u000b\fB\f\u000b\n\r\t ,C\tD\rE\nF\u000bG\fH I",
          "expected": [
            "a b",
            "c d e f g h i"
          ],
          "actual": [
            "a b",
            "c d e f g h i"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_quoted_whitespace",
          "input": "\" \t\r\n\u000b\fA  \t\t\r\n\u000b\fB\f\u000b\n\r\t \"",
          "expected": [
            " \t\r\n\u000b\fa  \t\t\r\n\u000b\fb\f\u000b\n\r\t "
          ],
          "actual": [
            " \t\r\n\u000b\fa  \t\t\r\n\u000b\fb\f\u000b\n\r\t "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all_escaped_whitespace",
          "input": "\\ \\\t\\\r\\\n\\\u000b\\\f\\ ",
          "expected": [
            " \t\r\n\u000b\f "
          ],
          "actual": [
            " \t\r\n\u000b\f "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_boundaries",
          "input": " \t\"  A  \"\r\n,  \\ B\\  \t, \" \" \tA\t \" \" ",
          "expected": [
            "  a  ",
            " b "
          ],
          "actual": [
            "  a  ",
            " b "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_breaks_runs",
          "input": "A \t\"\t\t\"\r\n B,A  \\  \t B",
          "expected": [
            "a \t\t b",
            "a   b"
          ],
          "actual": [
            "a \t\t b",
            "a   b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty_quotes_do_not_break_runs",
          "input": "A \"\"\t B, A\t B ,\"\" \t\"\",A\"\"B",
          "expected": [
            "a b",
            "ab"
          ],
          "actual": [
            "a b",
            "ab"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected_only_and_exact_dedup",
          "input": " ,\" \" ,\\ ,\"  \",\"\t\",\\\t,\" \t\",\"\"",
          "expected": [
            " ",
            "  ",
            "\t",
            " \t"
          ],
          "actual": [
            " ",
            "  ",
            "\t",
            " \t"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "dedup_after_normalization",
          "input": "B, A\t C ,\"A C\",A\\ C,a  c,\"A  C\",b,D,\"a  c\"",
          "expected": [
            "b",
            "a c",
            "a  c",
            "d"
          ],
          "actual": [
            "b",
            "a c",
            "a  c",
            "d"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "other_ascii_literals",
          "input": " 'AZ_09-!?:;[]{}()/+=.@#$%^&*|~`' ,\u0000A\u001cB\u001dC\u001eD\u001fE\u007f",
          "expected": [
            "'az_09-!?:;[]{}()/+=.@#$%^&*|~`'",
            "\u0000a\u001cb\u001dc\u001ed\u001fe\u007f"
          ],
          "actual": [
            "'az_09-!?:;[]{}()/+=.@#$%^&*|~`'",
            "\u0000a\u001cb\u001dc\u001ed\u001fe\u007f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escape_exactly_one_whitespace",
          "input": "\\  \t, \t\\ ,A\\\t\t\tB,\\\n\n",
          "expected": [
            " ",
            "a\t b",
            "\n"
          ],
          "actual": [
            " ",
            "a\t b",
            "\n"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_backslash_then_separator",
          "input": "A\\\\,B,C\\\\\\,D",
          "expected": [
            "a\\",
            "b",
            "c\\,d"
          ],
          "actual": [
            "a\\",
            "b",
            "c\\,d"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped_quote_then_real_toggle",
          "input": "A\\\"\"B,C\"D,\"E\\\"\"F,G",
          "expected": [
            "a\"b,cd",
            "e\"f",
            "g"
          ],
          "actual": [
            "a\"b,cd",
            "e\"f",
            "g"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing_escape_outside",
          "input": "GOOD,\"ALSO GOOD\",BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing_escape_inside",
          "input": "GOOD,OK,\"BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed_quote_mid_label",
          "input": "GOOD,SECOND,PRE\"BAD,TAIL",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped_final_quote_is_not_closing",
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
          "case": "empty_segments",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty_segments",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "order_and_ascii_case",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "order_and_ascii_case",
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
          "case": "dedup_after_normalization",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "dedup_after_normalization",
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
          "case": "escape_exactly_one_whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escape_exactly_one_whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_backslash_then_separator",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_backslash_then_separator",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped_quote_then_real_toggle",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped_quote_then_real_toggle",
          "property": "ascii_lowercase",
          "passed": true
        }
      ]
    },
    "executed_at": 1791381145.544462,
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