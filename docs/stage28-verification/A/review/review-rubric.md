# Common review rubric

Assess the seven frozen task criteria against original/candidate source and diff,
frozen independent design/harness, independent test result and candidate development
check results supplied in the review bundle. Both reviewers receive these same categories.
No held-out external suite, mutation outcomes or other candidate information is supplied.
Return the supplied REVIEW_SCHEMA. Concrete persistence/data-loss/API regressions are
blocking; scoped maintainability concerns are nonblocking. Distinguish missing evidence
from observed defects. Assess validation, transaction ownership, NULL-safe replay,
compatibility, scope and unnecessary complexity. Do not rank by test/file/line counts.
Reviewer must not write files or change candidate/tests. No new requirements.
