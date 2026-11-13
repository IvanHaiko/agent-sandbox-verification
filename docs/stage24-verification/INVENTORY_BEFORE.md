# Before-cleanup inventory

Recorded before deletion. JSON includes hashes and import edges for every file.

The native closure is native_codex_linux + WSL workflow + labels contract + optional WSL continuation roles.
All other old package imports form the manual rollback closure. No active native-to-legacy edge exists.

| Module | Class | Disposition |
|---|---|---|
| `agent_system/__init__.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/__main__.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/agent_transport.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/approvals.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/architecture.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/artifact_execution.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/chatgpt_oauth.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/chatgpt_plan_transport.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/cli.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/codex_tool_session.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/config.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/contexts.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/contracts.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/controller.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/errors.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/evaluation.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/evidence.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/experiments.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/gates.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/git.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/hardened_workflow.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/independent_tests.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/integration.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/isolation.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/isolation_probes.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/live.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/mechanical_gates.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/model_tool_boundary.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/native_codex.py` | HISTORICAL VALIDATION | Failed Windows native experiment; no active WSL dependency. |
| `agent_system/native_codex_linux.py` | KEEP | Validated native Linux launcher; rename permission profile and consolidate artifact/receipt helpers. |
| `agent_system/orchestrator.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/policies.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/responses_http.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/responses_lifecycle.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/roles.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/__init__.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/base.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/chatgpt_plan.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/docker_isolated.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/isolated_session.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runners/tool_docker.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/runtime_observability.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/state_machine.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/storage.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/task.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/telemetry.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/transport_diagnostics.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `agent_system/workflow.py` | LEGACY FALLBACK | Complete old package dependency closure archived for manual rollback; no active imports. |
| `tests/conftest.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/fake_codex.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/fake_live_codex.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/fake_workflow_codex.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_agent_transport.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_artifact_execution.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_chatgpt_oauth.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_chatgpt_plan_transport.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_contracts.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_docker_runner.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_evaluation_additional.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_hardened_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_hardening_isolation.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_hardening_tests.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_live.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_mechanical_gates.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_model_tool_boundary.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_native_codex.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_pilot0.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_responses_http_error.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_runner.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_runtime_observability.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_stage19_request_schema_audit.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_stage19c_reconciliation.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_stage19e_matrix.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_stage19g_enforcement.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_state_machine.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_telemetry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_transport_diagnostics.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_workflow_additional.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `tests/test_worktrees.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/collect_evidence.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/conftest.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/export_workflows.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/finalize_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/full_response_observer.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/regression_shards.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/role_driver.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage18_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage18_chatgpt_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage18_checkpoint.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage18c_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_authorized_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_final_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_final_smoke_retry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_finalize.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_request_audit.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_request_audit_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_request_schema_audit.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19_run_live.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_capture.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_capture_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_capture_result.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_full_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_full_response.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19b_native_replay.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19c_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19c_legacy_gate.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19c_reconciliation_model.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19d_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_final_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_final_smoke_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_live_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_live_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_matrix.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19e_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_admit_variant.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_assess_more.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_blocked_assessment.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_2.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_3.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_4.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_5.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_6.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_7.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_catalog_8.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_2.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_3.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_4.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_5.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_6.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_7.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_live_smoke_8.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_prepare_more.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage19g_reconnect_more.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage20_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage20_cleanup.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage20_preflight.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage20_report.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage20_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_catalog_retry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_catalog_retry3.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_preflight.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_preflight_retry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_retry3_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_workflow_retry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21_workflow_retry3.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage21a_observability.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_continuation_catalog.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_report.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_sol56.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_sol56_report.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage22_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage23_continuation_audit.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage23_discovery.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage23_labels_contract.py` | CONSOLIDATE | Promote verified behavior; discard historical gate/counter/driver scaffolding. |
| `validation/stage23_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage23_wsl_continuation.py` | CONSOLIDATE | Promote verified behavior; discard historical gate/counter/driver scaffolding. |
| `validation/stage23_wsl_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/stage23_wsl_workflow.py` | CONSOLIDATE | Promote verified behavior; discard historical gate/counter/driver scaffolding. |
| `validation/stage23b_wsl_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_chatgpt_signatures.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_codex_dynamic_tools.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_full_response_observer.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_real_isolation.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage18c_real.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19_final_smoke_driver.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19_final_smoke_retry.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19_reconnect.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19b_capture_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19b_capture_entrypoint.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19d_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19e_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19e_final_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19e_final_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19e_live_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_contained.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_current_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_2.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_3.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_4.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_5.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_6.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_7.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_live_smoke_8.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_repaired_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_2_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_4_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_5_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_6_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_7_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage19g_smoke_8_roundtrip.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage20_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage21_retry3_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage21_workflow.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage22_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage22_recovery.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage22_sol56_admission.py` | HISTORICAL VALIDATION | Old stage driver, test, example, configuration or assessment; snapshot preserved. |
| `validation/test_stage23_continuation.py` | CONSOLIDATE | Promote verified behavior; discard historical gate/counter/driver scaffolding. |
| `validation/test_stage23_wsl_workflow.py` | CONSOLIDATE | Promote verified behavior; discard historical gate/counter/driver scaffolding. |
