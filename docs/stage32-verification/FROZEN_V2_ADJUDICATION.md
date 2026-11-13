# Frozen v2 oracle adjudication — superseded, never edited

Authority: native parent, responsible for contract interpretation and repair
decisions. This decision is explicit and must be visible in final review/report.
No candidate or Implementer exists at this point.

Frozen v2 baseline execution produced **12 failures, 3 passes**, zero collection
errors. Eleven failures demonstrate the agreed missing admission guard. The extra
failure is the same-day retry test's gzip-file heuristic at line 152. It classifies
an existing gzip file as immutable merely because the **missing** HF repository's
name does not occur in that file. The documented partial aggregate contains only
successful rows so far; adding the missing row necessarily changes its gzip bytes.
The test has already checked that every earlier successful JSONL envelope remains
byte-identical. The contract promises preservation of successful observations and
skipping successful legs, not an unchanged partial aggregate when appending a row.

Decision: the gzip heuristic is an incorrect oracle. Do not change valid append
behavior to satisfy it. Preserve frozen-v2, freeze.json, frozen-baseline.json/XML
and their hashes. Tester must retain the envelope-byte assertions and check complete
leg gzip preservation using the public manifest's per-leg success state and `file`
name, or otherwise identify unaffected complete legs without the missing-row
heuristic. No production contract is changed. Record agreement or disagreement;
unresolved disagreement blocks implementation and requires escalation.

A corrected suite, if the independent Tester agrees, is a new **frozen-v3** with
a separate receipt. Validate the corrected draft against baseline *before*
freezing: only the eleven expected off-date admission failures may remain.
Reviewer receives both frozen versions, original failure and this adjudication.

This is one targeted frozen-oracle correction cycle, not an implementation repair.
There will be no silent edit to authoritative v2 or hidden oracle weakening.
