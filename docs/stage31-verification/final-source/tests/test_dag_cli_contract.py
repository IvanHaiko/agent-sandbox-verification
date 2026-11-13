"""
tasks/001: nothing in the repository previously connected dags/*.py to the
argparse parser in src/main.py. All 12 DAG tasks are BashOperators running
`python -m src.main <subcommand> ...`, so a subcommand renamed or removed on
the CLI side, or a flag renamed while its `dest=` stays the same, would fail
only at 6am in production -- the whole test suite would stay green.

This module reads dags/*.py as text rather than importing them: airflow is
not in requirements.txt for the local/CI test environment, and importing
would fail before a single assertion ran.

Second pass (2026-09-07, after the first review returned this task
`blocked`): the first version only checked the subcommand token, matched
double-quoted `bash_command`s with a single regex `.search()` (so a second,
chained `python -m src.main ...` in the same string was invisible), and only
asserted the extraction found *something* rather than an exact count. This
version:
- feeds the whole argument string after `python -m src.main` to the real
  `main.parse_args()` via `shlex.split`, so a flag rename that preserves
  `dest=` (main() itself unchanged) is still caught;
- uses `finditer`/`findall` throughout, and matches both quoting styles, so a
  second invocation in one `bash_command` or a single-quoted string is not
  silently dropped;
- discovers DAG files with `rglob`, not `glob`, so a DAG in a real
  subpackage is inside the contract (Airflow's DagBag scans recursively),
  while dot-directories are skipped -- see _dag_files();
- asserts an exact expected invocation count instead of "at least one", so
  losing most of the real invocations to a bad regex fails loudly instead of
  passing vacuously.
"""

import re
import shlex
import sys
from pathlib import Path

from src import main

DAGS_DIR = Path(__file__).resolve().parent.parent / "dags"

# Matches a bash_command= string in either quoting style. Only one of the two
# groups is populated per match.
BASH_COMMAND_RE = re.compile(r"""bash_command\s*=\s*(?:"([^"]*)"|'([^']*)')""")

# Everything after `python -m src.main` up to the next `&&` (a shell chain
# boundary) or a newline -- i.e. the argument string for one invocation.
# finditer, not search, so a chained second invocation in the same
# bash_command string is not lost.
INVOCATION_RE = re.compile(r"python -m src\.main\s+([^&\n]+)")

# Measured against the tracked dags/ tree: 11 invocations across the three
# DAGs (steam_etl_daily.py: 4, steam_etl_mapping.py: 3, steam_etl_weekly.py:
# 4). Deliberately counts only files git tracks in spirit -- see
# _dag_files() -- so the number is the same on a clean CI checkout as it is
# on a machine carrying local tooling artefacts.
EXPECTED_INVOCATION_COUNT = 11


def _dag_files() -> list[Path]:
    """
    DAG modules, recursively, minus dot-directories.

    rglob rather than glob so a DAG in a real subpackage (dags/common/x.py)
    is inside the contract -- Airflow's DagBag scans recursively, so such a
    file runs in production and its command lines must parse.

    Dot-directories are excluded because they are tooling artefacts, not
    deployable code: dags/.ipynb_checkpoints/ currently holds an untracked,
    gitignored copy of steam_etl_daily.py with four more invocations in it.
    Counting those would make EXPECTED_INVOCATION_COUNT machine-dependent --
    15 here, 11 on a clean CI checkout -- i.e. a test that fails for everyone
    who does not happen to have opened a DAG in Jupyter. That the checkpoint
    file exists at all, and would be a duplicate dag_id if it ever reached
    the container, is a separate defect recorded in ROADMAP.md; it is not
    this contract's job to fail over it.
    """

    return sorted(
        path
        for path in DAGS_DIR.rglob("*.py")
        if not any(part.startswith(".") for part in path.relative_to(DAGS_DIR).parts)
    )


def _dag_invocations() -> list[tuple[Path, str]]:
    """
    Every `python -m src.main ...` invocation found in a `bash_command=`
    string across dags/*.py (recursively), as (dag_file, argument_string)
    pairs. `argument_string` is everything between the subcommand and the end
    of that invocation -- not just the subcommand token.
    """

    invocations: list[tuple[Path, str]] = []

    for dag_file in _dag_files():
        text = dag_file.read_text(encoding="utf-8")

        for bash_command_match in BASH_COMMAND_RE.finditer(text):
            bash_command = (
                bash_command_match.group(1)
                if bash_command_match.group(1) is not None
                else bash_command_match.group(2)
            )

            for invocation_match in INVOCATION_RE.finditer(bash_command):
                invocations.append((dag_file, invocation_match.group(1).strip()))

    return invocations


def test_dags_reference_the_expected_number_of_subcommand_invocations():
    """
    Guards against the "every invocation parses" test below quietly
    checking fewer command lines than exist: an invocation deleted from a
    DAG, or a file dropped from discovery, fails here.

    What it does *not* currently prove, measured rather than assumed: every
    tracked bash_command is double-quoted, holds exactly one invocation, and
    sits directly in dags/, so narrowing BASH_COMMAND_RE to double quotes,
    finditer to search, or rglob to glob each still finds the same 11 real
    invocations and this test stays green. Those three narrowings are
    guarded by construction, not by this assertion. Proving them needs a
    fixture DAG tree carrying the three shapes -- see ROADMAP.md.
    """

    invocations = _dag_invocations()

    assert len(invocations) == EXPECTED_INVOCATION_COUNT, (
        f"expected {EXPECTED_INVOCATION_COUNT} `python -m src.main ...` "
        f"invocations under {DAGS_DIR} (recursively), found "
        f"{len(invocations)}: {invocations}"
    )


def test_every_dag_command_line_parses_with_the_live_cli():
    """
    Every `python -m src.main <subcommand> <flags...>` line a DAG actually
    runs must parse with the real argparse parser -- the whole line, not just
    the subcommand token. Catches a flag rename that keeps `dest=` the same
    (so main() itself is untouched and every hand-built-Namespace dispatch
    test in test_main.py stays green) but breaks the command line the DAG
    sends on the wire, e.g. `--limit` renamed to `--max-observed` at
    src/main.py:1576 while dags/steam_etl_mapping.py:23 still sends
    `--limit`. Also catches an unregistered/renamed subcommand and a
    single-quoted bash_command referencing one, since parsing fails the same
    way regardless of which quote style extracted it.
    """

    invocations = _dag_invocations()
    failures: dict[str, str] = {}

    original_argv = sys.argv
    try:
        for dag_file, arg_string in invocations:
            tokens = shlex.split(arg_string)
            sys.argv = ["prog", *tokens]
            try:
                main.parse_args()
            except SystemExit:
                failures[f"{dag_file}: {arg_string}"] = arg_string
    finally:
        sys.argv = original_argv

    assert failures == {}, (
        "dags/*.py command lines that src/main.py's live argparse parser "
        f"rejects: {failures}"
    )
