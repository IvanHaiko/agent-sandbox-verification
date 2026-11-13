# Historical architecture and experiments

Everything in this directory records earlier stages. It does not describe current
runtime behavior. The [current architecture](../../README.md) is the source of truth.

Final assessments remain readable with their original evidence paths:

- [Stage20](STAGE20_FIRST_MULTI_AGENT_WORKFLOW.md)
- [Stage21](STAGE21_DEFECT_DETECTION_ASSESSMENT.md)
- [Stage21A](STAGE21A_RUNTIME_OBSERVABILITY_ASSESSMENT.md)
- [Stage22](STAGE22_SIMPLIFIED_EXECUTION_ASSESSMENT.md)
- [Stage23](STAGE23_NATIVE_CODEX_BACKEND_ASSESSMENT.md)
- [Stage23 Windows prerequisites](STAGE23A_NATIVE_RUNTIME_PREREQUISITES.md)
- [Stage23B WSL smoke](STAGE23B_WSL_NATIVE_SMOKE.md)

`pre-cleanup.zip` preserves every inventoried source, test, validation driver,
configuration, example and historical document/evidence file at its original
repository-relative path. The complete old package dependency closure is retained
because this checkout has no Git history. It includes the former custom transport
and failed Windows experiment. It is not an importable installed package or an
automatic fallback. Restore into a separate directory for explicit manual rollback.

[Inventory and hashes](../stage24-verification/inventory-before.json) and
[verified archive receipt](../stage24-verification/archive-receipt.json) record the
snapshot. Old scripts are historical and are not part of test discovery. Important
later evidence is also expanded here so links from the final assessments continue
to work; early/redundant evidence is stored only in the compressed snapshot.
