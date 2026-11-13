---
{
  "title": "Acceptance and integrity",
  "summary": "Apply scope, frozen-input and preservation guarantees.",
  "status": "current",
  "related_files": [
    "agent_system/acceptance.py",
    "tests/test_support.py",
    "examples/native_smoke.py"
  ]
}
---

# Acceptance and integrity

`agent_system/acceptance.py` provides workspace creation, snapshots, test freezing,
acceptance, preservation and cleanup. The [reference](reference.md) has the API example.

- Construct private role workspaces from explicit relative paths and bytes.
- Preserve the source baseline before implementation. Inspect the complete final
  workspace, including additions, deletions and hidden files, against allowed paths.
- For high-risk work, freeze public tests and the contract outside worker writable
  paths before candidate creation or exposure. Frozen versions never change in repair.
- Supply all actual required process and check outcomes to `accept`; it executes
  nothing. Missing, failing or incomplete outcomes cannot become invented successes.
- Review includes compatibility, test semantics and failures, not only green counts.
- Preserve rejected bytes and diagnostics before cleanup. Archives must be fresh;
  failed preservation leaves the private workspace available for diagnosis.

Snapshots reject links. An unchanged primary file with an authorized helper-only
repair can be valid: required final files and allowed changed paths are distinct.
Disputed test expectations require explicit adjudication and a new frozen version;
retain the original failure.

## Protecting an existing Git checkout

Preserve both logical repository state (HEAD/branch, `git ls-files --stage -z`,
staged and working binary diffs, untracked source and protected-file hashes, and
worktree registry) and the original index bytes. Save the index bytes and hash
**before any Git inspection**, resolving the actual index location for linked
worktrees. Run inspections with `GIT_INDEX_FILE` pointing to a disposable copy and
`GIT_OPTIONAL_LOCKS=0`; for enforced protection, expose the original checkout and
Git metadata read-only through the Linux sandbox. Export selected source into an
owned workspace without registering a worktree in the original. Never refresh,
reset or restore the protected index. Git 2.53.0 `diff --binary` was observed
refreshing cached stat data even with optional locks disabled; that variable alone
does not enforce byte preservation.

Report logical preservation and raw-index preservation separately. Compare the
saved original bytes again after inspection and at closeout, and retain any
mismatch with the command evidence. A stat-cache-only change can preserve staged
content but still fails the explicit raw-byte invariant for protected runs;
matching logical state never overrides that failure. See
`STAGE33_INTEGRITY_AND_COMPATIBILITY_REPORT.md` for the focused reproduction.
