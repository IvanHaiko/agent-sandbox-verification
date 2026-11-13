# Pre-freeze test admission adjudication

The parent retained Tester draft v1 bytes/hashes and executed it against the
unchanged source baseline: 13 failures, 2 passes (`draft-v1-baseline.json`). Eleven
failures concern the selected missing date-admission guarantee. Two failures are
fixture/oracle errors and must not drive production behavior:

1. Default partition: `now=clock` is a timestamp injection; it does not redefine
   the public `collector.run.utc_today()` used by an omitted snapshot_date. The
   contract explicitly preserves default today-UTC behavior. A deterministic test
   must control that public date interface or use a consistent real current clock.
2. Same-day retry: `FakeHttp` defaults Vendor/Gone to HTTP 401. Replacing its entire
   `hf_status` map removed this permanent failure, allowing an extra real fixture
   observation. Comparing with a default reference then incorrectly rejects that
   extra row. The fixture must preserve unrelated permanent failures when injecting
   the selected transient failure.

The Tester receives only this public fixture clarification, its own draft, and the
unchanged contract. No source implementation, candidate, proposed fix, private
handoff, or other role workspace is exposed. The parent asks for corrections of
these two tests only, retaining all defect and compatibility assertions. The
superseding draft is v2. No authoritative frozen version exists yet and no
Implementer has launched. Correct production code will not be changed to satisfy
the rejected expectations.

The initial pytest invocation failed before collection because scratch TMPDIR
was not set. That actual result is preserved separately in
`draft-v1-environment-failure.json`; no input permissions were weakened.
