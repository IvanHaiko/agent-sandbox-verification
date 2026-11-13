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
  },
  "canonical_contract": {
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
    ],
    "clarifications": [
      {
        "rules": [
          1,
          2,
          3,
          8
        ],
        "clarification": "Escaped commas and quotes are literal characters, regardless of quoted mode. Quoting and escaping do not exempt emitted ASCII letters from lowercasing."
      },
      {
        "rules": [
          5,
          6,
          7
        ],
        "clarification": "Boundary trimming applies only to ordinary whitespace. Protected whitespace remains exact and separates ordinary-whitespace runs; removed quote delimiters emit no character."
      },
      {
        "rules": [
          4,
          9,
          10
        ],
        "clarification": "Malformed quoting or escaping invalidates the entire input, including otherwise valid preceding labels. Empty-label removal and deduplication do not suppress ValueError."
      },
      {
        "rules": [
          7,
          9,
          10
        ],
        "clarification": "Protected whitespace-only labels remain eligible for exact-string deduplication. Equality is based on normalized output strings, not their quoting or escaping in the input."
      }
    ],
    "risks": [
      "Losing whitespace protection can incorrectly trim boundaries, collapse protected characters, or discard nonempty labels.",
      "Confusing escaped literals with delimiters can change label boundaries or quoted mode.",
      "Returning preceding labels after malformed trailing input violates whole-input failure.",
      "Deduplicating before normalization or ignoring exact whitespace differences can alter membership or first-occurrence order."
    ]
  },
  "candidate_diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_whitespace = False\n+            continue\n+        elif character in whitespace and not quoted:\n+            # Delay ordinary whitespace to trim boundaries and collapse runs.\n+            if characters:\n+                pending_whitespace = True\n+            continue\n+\n+        if pending_whitespace:\n+            characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
  "implementation_handoff": {
    "role": "implementer",
    "execution_status": "completed",
    "model": "gpt-6.1-sol",
    "changed_files": [
      "src/normalize_labels.py"
    ],
    "candidate_hashes": {
      "src/normalize_labels.py": "0b2ce5ad60e46b898a9b1da9eccdbe4e9c514950a3aa7c0d8d502a8aeba08f49"
    },
    "diff": "--- a/src/normalize_labels.py\n+++ b/src/normalize_labels.py\n@@ -1,2 +1,48 @@\n def normalize_labels(value: str) -> list[str]:\n-    raise NotImplementedError\n+    labels: list[str] = []\n+    seen: set[str] = set()\n+    characters: list[str] = []\n+    quoted = False\n+    escaped = False\n+    pending_whitespace = False\n+    whitespace = \" \\t\\r\\n\\v\\f\"\n+\n+    def finish_label() -> None:\n+        label = \"\".join(characters)\n+        if label and label not in seen:\n+            seen.add(label)\n+            labels.append(label)\n+        characters.clear()\n+\n+    for character in value:\n+        if escaped:\n+            escaped = False\n+        elif character == \"\\\\\":\n+            escaped = True\n+            continue\n+        elif character == '\"':\n+            quoted = not quoted\n+            continue\n+        elif character == \",\" and not quoted:\n+            finish_label()\n+            pending_whitespace = False\n+            continue\n+        elif character in whitespace and not quoted:\n+            # Delay ordinary whitespace to trim boundaries and collapse runs.\n+            if characters:\n+                pending_whitespace = True\n+            continue\n+\n+        if pending_whitespace:\n+            characters.append(\" \")\n+            pending_whitespace = False\n+        if \"A\" <= character <= \"Z\":\n+            character = chr(ord(character) + 32)\n+        characters.append(character)\n+\n+    if escaped:\n+        raise ValueError(\"Trailing unpaired backslash\")\n+    if quoted:\n+        raise ValueError(\"Unclosed double quote\")\n+    finish_label()\n+    return labels\n",
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
    "design_sha256": "77a9fbbfa9c1b6de9fd538caa65ef8f3c71652bff3797c29b4726958165f65bc",
    "case_count": 24,
    "candidate_blind_before_freeze": true,
    "frozen_before_exposure": true
  },
  "deterministic_acceptance": {
    "model_requests": 0,
    "tester_sessions": 0,
    "returncode": 0,
    "design_sha256": "77a9fbbfa9c1b6de9fd538caa65ef8f3c71652bff3797c29b4726958165f65bc",
    "harness_sha256": "6537706d40983836632d206be534a6ef67c4edaa58c03a3e8cb32fec33d54b82",
    "candidate_sha256_before": "0b2ce5ad60e46b898a9b1da9eccdbe4e9c514950a3aa7c0d8d502a8aeba08f49",
    "candidate_sha256_after": "0b2ce5ad60e46b898a9b1da9eccdbe4e9c514950a3aa7c0d8d502a8aeba08f49",
    "mutation_scope_valid": true,
    "result": {
      "passed": true,
      "interface": true,
      "cases": [
        {
          "id": "empty-input",
          "input": "",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "empty-label-forms",
          "input": ",,,\"\", \t\r\n\u000b\f,\"\"\"\",,",
          "expected": [],
          "actual": [],
          "error": null,
          "passed": true
        },
        {
          "id": "separator-order",
          "input": ", BETA ,, Alpha, GAMMA, beta, ,",
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
          "id": "quote-concatenation",
          "input": "PRE\"MiD\"POST,\"A\"B\"C\"\"D\",X\"\"Y",
          "expected": [
            "premidpost",
            "abcd",
            "xy"
          ],
          "actual": [
            "premidpost",
            "abcd",
            "xy"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "quoted-commas",
          "input": "\"A,B,,C\",D\",E\"F,\",\"",
          "expected": [
            "a,b,,c",
            "d,ef",
            ","
          ],
          "actual": [
            "a,b,,c",
            "d,ef",
            ","
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped-delimiters-outside",
          "input": "A\\,B,A\\\"B,A\\\\B",
          "expected": [
            "a,b",
            "a\"b",
            "a\\b"
          ],
          "actual": [
            "a,b",
            "a\"b",
            "a\\b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped-delimiters-inside",
          "input": "\"A\\,B\\\"C\\\\D\",END",
          "expected": [
            "a,b\"c\\d",
            "end"
          ],
          "actual": [
            "a,b\"c\\d",
            "end"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all-ordinary-whitespace",
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
          "id": "all-quoted-whitespace",
          "input": "\" \t\r\n\u000b\fA  \t\tB\f\u000b\n\r\t \"",
          "expected": [
            " \t\r\n\u000b\fa  \t\tb\f\u000b\n\r\t "
          ],
          "actual": [
            " \t\r\n\u000b\fa  \t\tb\f\u000b\n\r\t "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "all-escaped-whitespace",
          "input": "\\ \\\t\\\r\\\n\\\u000b\\\fA\\ \\ B\\\f\\\u000b\\\n\\\r\\\t\\ ",
          "expected": [
            " \t\r\n\u000b\fa  b\f\u000b\n\r\t "
          ],
          "actual": [
            " \t\r\n\u000b\fa  b\f\u000b\n\r\t "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "protected-breaks-runs",
          "input": "A \t\"\t\t\"\r\n B,A \t\\\t\r\n B",
          "expected": [
            "a \t\t b",
            "a \t b"
          ],
          "actual": [
            "a \t\t b",
            "a \t b"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "mixed-protected-boundaries",
          "input": " \t\"  \"A\"\t\" \r, \n\\ B\\\t\f ",
          "expected": [
            "  a\t",
            " b\t"
          ],
          "actual": [
            "  a\t",
            " b\t"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "empty-quotes-do-not-break-runs",
          "input": " \"\" A \t\"\"\r\n B \"\" ,\"\" \t\"\"",
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
          "id": "protected-only-and-dedup",
          "input": "\" \t\r\n\u000b\f\",\\ ,\" \",\"  \",\"\", \t",
          "expected": [
            " \t\r\n\u000b\f",
            " ",
            "  "
          ],
          "actual": [
            " \t\r\n\u000b\f",
            " ",
            "  "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "dedup-after-all-normalization",
          "input": " Z,ALPHA,\"z\",a\\LPHA, alpha ,BETA,Z,\"BE\"TA",
          "expected": [
            "z",
            "alpha",
            "beta"
          ],
          "actual": [
            "z",
            "alpha",
            "beta"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "exact-whitespace-equality",
          "input": "A B,A\tB,\"A B\",\"A  B\",A\\ B,\" A B \"",
          "expected": [
            "a b",
            "a  b",
            " a b "
          ],
          "actual": [
            "a b",
            "a  b",
            " a b "
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "other-ascii-literals",
          "input": "AZ09!@#$%^&*()_+-=[]{};:'/?<>.|~`\u0000\u001b\u007f",
          "expected": [
            "az09!@#$%^&*()_+-=[]{};:'/?<>.|~`\u0000\u001b\u007f"
          ],
          "actual": [
            "az09!@#$%^&*()_+-=[]{};:'/?<>.|~`\u0000\u001b\u007f"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "escaped-uppercase-both-modes",
          "input": "\\A\\Z,\"\\A\\Z\",\\n\\t\\r",
          "expected": [
            "az",
            "ntr"
          ],
          "actual": [
            "az",
            "ntr"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "paired-backslash-before-delimiter",
          "input": "A\\\\,B,\"C\\\\\",D\\\\",
          "expected": [
            "a\\",
            "b",
            "c\\",
            "d\\"
          ],
          "actual": [
            "a\\",
            "b",
            "c\\",
            "d\\"
          ],
          "error": null,
          "passed": true
        },
        {
          "id": "trailing-escape-outside",
          "input": "OK,ok,,\"\",BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "trailing-escape-inside",
          "input": "OK,\"BAD\\",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "unclosed-quote-after-valid-labels",
          "input": "OK,ok,NEXT,PRE\"BAD,TAIL",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "escaped-quote-does-not-close",
          "input": "OK,\"BAD\\\"",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        },
        {
          "id": "empty-normalization-cannot-hide-error",
          "input": ",\"\", \t,\"",
          "expected": null,
          "actual": null,
          "error": "ValueError",
          "passed": true
        }
      ],
      "properties": [
        {
          "case": "empty-input",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty-input",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "empty-label-forms",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty-label-forms",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "separator-order",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "separator-order",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quote-concatenation",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quote-concatenation",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "quoted-commas",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "quoted-commas",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped-delimiters-outside",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped-delimiters-outside",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped-delimiters-inside",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped-delimiters-inside",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all-ordinary-whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all-ordinary-whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all-quoted-whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all-quoted-whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "all-escaped-whitespace",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "all-escaped-whitespace",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected-breaks-runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected-breaks-runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "mixed-protected-boundaries",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "mixed-protected-boundaries",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "empty-quotes-do-not-break-runs",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "empty-quotes-do-not-break-runs",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "protected-only-and-dedup",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "protected-only-and-dedup",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "dedup-after-all-normalization",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "dedup-after-all-normalization",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "exact-whitespace-equality",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "exact-whitespace-equality",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "other-ascii-literals",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "other-ascii-literals",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "escaped-uppercase-both-modes",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "escaped-uppercase-both-modes",
          "property": "ascii_lowercase",
          "passed": true
        },
        {
          "case": "paired-backslash-before-delimiter",
          "property": "unique_nonempty_labels",
          "passed": true
        },
        {
          "case": "paired-backslash-before-delimiter",
          "property": "ascii_lowercase",
          "passed": true
        }
      ]
    },
    "executed_at": 1791389039.4981484,
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