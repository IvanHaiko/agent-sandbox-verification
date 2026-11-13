# Stage 26 framework changes

The reusable capability is `agent_system/test_environment.py`: a Controller-owned predefined-check service. A network-disabled role writes a named request inside its workspace; the Controller executes that fixed pytest or Ruff command through the existing native sandbox in a private user/network namespace. Results and source hashes are retained outside role reach. Commands, environment and database capability come from the Controller, not role requests. No shell/backend/model transport is added.

`NativeLinuxCodexRunner.run` accepts an optional Implementer test environment, grants only its exchange subtree, starts/stops it around the existing native invocation, cleans exchange files before mutation validation, and records check receipts. Model network permissions remain unchanged.

`validation/steam_runtime.py` accepts the Stage 26 disposable root and forces pinned dependency installation into the private virtual environment, rather than relying on globally satisfied packages outside sandbox visibility. It clears inherited Python path overrides for pip.

`validation/steam_workflow.acceptance_and_review` retains Stage 25 defaults while permitting a Stage 26 independent module name and review focus. Candidate reconstruction, freeze checks, contained acceptance and read-only review are reused.

`validation/steam_refactoring.py` is the bounded experiment driver. It uses the same fixed-source archive, private workspaces, native runner, artifact validation and cleanup. It adds the task's baseline compatibility and two predeclared behavior controls, rather than a generic task DSL or new orchestrator.

`tests/test_test_environment.py` adds three focused tests for unknown-command rejection, failure/source-hash evidence, exchange cleanup and rejection of source mutation. Existing launcher isolation regression tests are retained.

The executed source and tests are archived under `executed-source/` with `executed-source-manifest.json`. The source workspace has no Git metadata. This Stage delivers a target Git patch and an inspectable framework working-tree change, not a framework commit.
