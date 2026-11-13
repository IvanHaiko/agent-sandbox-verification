# Stage 33 — Git index integrity and Python compatibility

Executed 10 October 2026 (Europe/Berlin). **Stage 33: PASS.**
Stage 32's official **PARTIAL** verdict and all its evidence remain unchanged.

## A. Executive summary

A concrete protection defect was reproduced: WSL Git 2.53.0 `diff --binary`
can refresh index stat caches even with `GIT_OPTIONAL_LOCKS=0`. The recorded
Stage 32 audit used that operation. Disposable reproductions changed raw index
hashes while preserving staged entries and working files. This supplies a strong,
evidence-based explanation consistent with the historical discrepancy, not proof
of its exact byte difference or exclusive cause. The original initial bytes do
not exist in the evidence.

The smallest correction is documented protection using a private index copy,
read-only original mounts and separate logical/raw acceptance. It was validated
on a disposable repository. Actual **Python 3.10.22 and 3.12.15** each passed
15 unchanged frozen acceptance tests, 143 project regressions and Ruff. No
engineering-candidate changes were necessary.

## B. Git index findings

**Confirmed historical observations.** `original-integrity.json` establishes
matching HEAD, branch, status, staged/working binary-diff hashes, worktree
registry, 407 captured tracked/untracked file hashes and 316 historical hashes.
Only the index hash differed:

| Observation | SHA-256 |
|---|---|
| Stage 32 initial index | `c963d3c70bbf461abb021dcb37173f9c8e8c2d203e22d649f96436cb2388b3fc` |
| Stage 32 saved final index; Stage 33 before/after | `ffeadd5362e1a64618e5e6d21cc8e061892ec37371f02e31da2b487d2f6f2c75` |
| Refined disposable replica before diff | `ffeadd5362e1a64618e5e6d21cc8e061892ec37371f02e31da2b487d2f6f2c75` |
| Refined disposable replica after diff | `902def7c355c28af2b4231e36cc211f262aff795c5163bb9a590db34657137a8` |

The saved/current index is 46,324 bytes, `DIRC` version 2, with 401 entries.
Git's own `ls-files --debug` supplies metadata diagnostics; no custom index parser
was introduced. Relevant configuration is repository format 0, filemode false,
symlinks false and ignorecase true. No auto-refresh override or split-index,
untracked-cache or fsmonitor configuration was found in the inspected settings.

**Parent execution evidence.** The actual Stage 32 parent trace and retained
`baseline.py` show optional locks disabled for status and audit calls. Crucially,
`fingerprint()` hashes the index **before** calling `git diff --binary`; there is
no immediate post-command byte check. The saved final index's mtime is
**12:15:50.253402 Europe/Berlin**, during the initial baseline process launched
at 12:15:17 and polled through 12:15:49. That timing supports an early audit-side
refresh; it does not independently identify the writer. Selected actual tool-call
excerpts, timestamps and the parent-trace hash are retained.

**Reproducible behavior.** Experiments used private refs/config/index/working
files. The source-state replica borrowed original Git objects only for reads;
all mutation operations targeted disposable metadata. The recorded sequence was
replayed: tracked/untracked enumeration, index path, HEAD, branch, status,
worktree list, cached binary diff and working binary diff. Only the last operation
changed index bytes. Its `ls-files --stage -z` hash and every working-file hash
remained identical. An initial credential-excluding export also omitted the public
`.env.example`; adding that template from HEAD produced the refined reproduction
above, whose binary working diff exactly matches Stage 32's recorded diff hash.
No credential file was loaded.

A three-file repository with staged, unstaged and untracked changes isolated the
mechanism. Touching an otherwise unchanged tracked file made its stat cache stale:

| Operation on stale disposable index | Raw bytes | Staged entries/files |
|---|---|---|
| Status, optional locks disabled | Unchanged | Unchanged |
| Working binary diff, optional locks disabled | Changed | Unchanged |
| Status, default locks | Changed | Unchanged |
| Diff with `diff.autoRefreshIndex=false` | Unchanged | Unchanged |
| Diff using private index, protected original read-only | Original unchanged; private changed | Unchanged |

For the small diff reproduction, index hash changed from
`e1b4fec6188c9f62b5407ddf2d69b7f8ce1a70f48ee3386a083a3e3fc844f5fd` to
`cfae71f7fcb4a6f3791b3e4e156aff280809dc62eaeccafae35dbbc1a2cfd3cb`.
Git's debug output shows only `cached.txt` ctime/mtime changing; size and staged
paths/modes/blob IDs/stages remained identical. The replica also refreshed cached
timestamps/device/inode values. Extension/serialization changes are not needed
to explain these reproductions, but cannot be excluded for the missing historical
before-image. Every operation's hash, command and exit is retained.

Git documents auto-refresh as the default for working-tree porcelain diffs.
The matching upstream implementation calls `refresh_index_quietly()` after stat
mismatches and takes an index lock without an optional-lock check in that path.
These sources support the observed mechanism:
[Git 2.53 diff documentation](https://git-scm.com/docs/git-diff/2.53.0#Documentation/git-diff.txt-diffautoRefreshIndex),
[Git 2.53 implementation](https://github.com/git/git/blob/v2.53.0/builtin/diff.c).

**Inference and uncertainty.** Audit-driven stat refresh is the best-supported
explanation. The exact `c963… → ffea…` transition cannot be reconstructed; initial
entry flags/extensions and the exclusive historical writer remain unknown.
An unobserved external operation is neither demonstrated nor ruled out. Matching
historical diff/status receipts support observable staging equivalence, not proof
of every original index flag.

## C. Corrective changes

- **`README.md`:** adds the protection procedure and explicit acceptance semantics.
  Save actual index bytes before any Git inspection, use a disposable
  `GIT_INDEX_FILE` plus optional locks disabled, expose original source/metadata
  read-only for enforced inspection, and compare original bytes after inspection
  and closeout. This addresses the reproduced audit write and the demonstrated
  missing-before-image diagnostic gap. Source export must not register worktrees
  in the original.
- **This report:** records Stage 33 results without altering historical reports.
- **One-stage diagnostic scripts under `.test-tmp/stage33/`:** `inspect_traces.py`,
  `original_audit.py`, `provision.py`, `git_experiments.py`, `verify.py`,
  `validate_protection.py`, `replica_diff.py`, `refine_replica.py`.
  Receipts, hashes, XML and metadata diagnostics are in
  `docs/stage33-verification/`. These are retained investigation material, not
  installed framework/orchestration modules.

The procedure validation observed errno 30 when write-opening the protected
disposable index. The identical diff then refreshed only a private index,
returned exit 0 and preserved original bytes, staged entries and working files.
The additional `diff.autoRefreshIndex=false` check also preserved bytes, but the
procedure uses private-index and filesystem isolation as its protection boundary.

Logical preservation concerns HEAD/branch, staged paths/content/modes/stages,
unstaged changes, untracked source, registry and protected-file content. Stat-cache
changes alone need not damage those semantics. **Raw byte preservation remains
an additional explicit invariant for protected originals.** A raw mismatch still
blocks that guarantee even when logical comparisons pass. No acceptance bypass,
framework-source edit, candidate edit, dependency-file change or correction commit
was introduced. No merge or push occurred.

## D. Python compatibility matrix

Candidate: engineering commit `c2358aaaf2c53bd2326562047f89ab2f6c1c4892`,
exported from the owned Stage 32 repository and checked against committed bytes.

| Check | Python 3.10 | Python 3.12 |
|---|---|---|
| Interpreter executed | CPython 3.10.22 | CPython 3.12.15 |
| Frozen Stage 32 v3 acceptance | 15 passed; 0 failures/errors/skips | 15 passed; 0 failures/errors/skips |
| Project regression suite | 143 passed; 0 failures/errors/skips | 143 passed; 0 failures/errors/skips |
| Ruff | 0.6.9; passed, exit 0 | 0.6.9; passed, exit 0 |
| Historical fixture integrity | 326/326 unchanged | 326/326 unchanged |

All final check processes exited 0 without timeout or surviving owned process
groups. Declared `requirements-dev.txt`/`requirements.txt` were installed in
separate disposable environments using uv 0.13.0. Both resolved requests 2.32.3,
pytest 8.3.3, PyArrow 25.0.1 and Ruff 0.6.9. Full interpreter build strings,
every installed dependency version, exact argv/cwd, outputs, exits and JUnit
counts are in `linux-*-runtime.json`, `dependencies-*.json`, the per-check receipts
and `linux-compatibility.json`.

The unchanged tests cover UTC admission, both `Z` and `+00:00` timestamp forms,
same-day retry, off-date refusal before HTTP/writes, completed exact no-ops and
real historical archive validation. No extra version-specific tests were needed.
Final commands retain Stage 32's pytest options, including `-p tests.conftest` for
the frozen suite, `-p no:cacheprovider`, project scratch basetemps/JUnit outputs,
and `ruff check --no-cache .`.

Checks used existing Linux confinement with clean environment, source/runtime/
frozen inputs read-only, only project `.scratch/` writable and network disabled.
Probes observed errno 30 for candidate/fixture/frozen write-opens, errno 2 for the
original index, and errno 1 for creating an Internet socket. No production API,
credentials, original environment or historical output was used for writes.

Initial runs on `/mnt/c` failed before tests ran: pytest's temporary capture-file
`truncate()` raised `FileNotFoundError` inside confinement, on both interpreters.
Those exit-1 outputs remain in the unprefixed receipts and `compatibility.json`.
Using project-owned native Linux temporary directories resolved the environment
failure without changing candidate, frozen tests, dependencies or test options.
uv's parent-project Python >=3.11 provisioning warning concerns this framework;
the candidate declares >=3.10 and executed successfully. Two new uv convenience
links into the disposable runtimes were removed; cleanup receipts are retained.

## E. Repository protection

Final original state exactly matches both the Stage 33 baseline and Stage 32's
saved final snapshot: HEAD `5121dd47adb2b69b2f64cca66609ebf8bd161868`, branch
`main`, existing status, empty staged diff, working diff, registry, 407 captured
file hashes and 316 historical hashes. Original index bytes, size and mtime also
match. Its 401 staged entries hash to
`2323efb6ea76c6a4faa6678d582aa715c79412eed7c5191e95c41744629c7ae1`
before/after. Audits used private index copies; no original index write/reset/
refresh/restore was attempted. Before/after bytes are now retained.

All 94 Stage 32 evidence/report files are hash-identical to this stage's baseline,
including failed receipts and frozen tests. Both verification exports preserved
all input hashes and all 326 copied historical/validation fixtures. The owned
engineering repository remains clean at the existing engineering commit.
Ignored derived outputs and excluded credential/private files were not audited
byte-for-byte; the historical initial index cannot be inspected or restored.

## F. Remaining limitations

Historical attribution remains inferential; no original before-image or complete
writer trace exists. Git experiments establish behavior of the installed WSL Git,
not every Git version/platform or extension. The original Windows Git sequence
was inspected in traces, not separately replayed. Dependency verification covers
the recorded resolved versions on Linux/WSL, not all allowed future resolutions
or Windows-native Python. Live providers and deployment were intentionally not
executed. Stage 32's admission/midnight/concurrency limitations remain unchanged.

## G. Final verdict

**PASS.** Both required Python versions were actually verified. A concrete
repository-protection failure mechanism was reproduced, a minimal documented
correction was validated, and the stronger raw-byte guarantee remains enforced
in future acceptance semantics. This does not reconstruct missing history or
retroactively change **Stage 32: PARTIAL**.
