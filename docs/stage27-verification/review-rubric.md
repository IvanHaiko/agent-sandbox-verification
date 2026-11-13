# Common review rubric (frozen before runs)

Assess functional contract compliance, existing caller compatibility, per-file atomicity,
lexical correctness at region/token boundaries, maintainability, complexity proportional
to the bounded task, duplication, stable public interfaces, coherent module placement,
and unnecessary dependencies. Cite concrete file/line evidence for findings. Distinguish
blocking behavioral defects from nonblocking improvements and already tested properties.
Do not reward control formality, test count, speed or architectural preference as code quality.
Return accept, reject, or request-fix plus blockers, findings and rationale. Do not edit code.

Independent testing quality: map tests to the seven contract requirements; evaluate
behavioral assertions, real database evidence and predeclared mutation sensitivity.
Count distinct meaningful defects, not failing parameterizations. Separate test defects
and environment errors from candidate defects. No numeric aggregate quality score.

Decision: KEEP, SIMPLIFY, REPLACE or INCONCLUSIVE based on observed comparable outcomes.
One task provides directional evidence only. Missing or unequal execution/model evidence
can make an architecture decision inconclusive even when useful candidate code exists.
