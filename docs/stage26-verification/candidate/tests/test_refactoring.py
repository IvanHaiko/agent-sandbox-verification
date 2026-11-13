"""Focused contracts for Steam Store preparation and ordered persistence."""

import copy
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src import load
from src.db import get_db_connection
from src.extract_steam_store import ENVELOPE_VERSION
from src.transform import _prepare_steam_store_load

FETCHED_AT = "2026-08-12T12:00:00+00:00"


def envelope(outcome, **changes):
    result = {
        "envelope": ENVELOPE_VERSION,
        "outcome": outcome,
        "appid": 100,
        "fetched_at": FETCHED_AT,
        "body": {"80": {"success": True, "data": {"steam_appid": 80, "name": "target"}}},
        "redirect_to": 90,
    }
    result.update(changes)
    return result


def run_file(monkeypatch, payload):
    monkeypatch.setattr(load, "load_json_file", lambda path: payload)
    return load.load_steam_store_file(Path("bronze.json"), "2026-08-12")


@pytest.mark.parametrize("appid", [None, 0, False, ""])
@pytest.mark.parametrize("outcome", ["refused", "not_found", "transport_error", "redirected", "unknown"])
def test_falsy_appid_precedes_malformed_body(monkeypatch, appid, outcome):
    def forbidden(*args, **kwargs):
        pytest.fail("early return performed a database effect")

    monkeypatch.setattr(load, "get_db_connection", forbidden)
    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", forbidden)
    assert run_file(monkeypatch, envelope(outcome, appid=appid, body=[1])) == outcome


@pytest.mark.parametrize("outcome, changes, message", [
    ("refused", {}, "Steam Store returned success=false"),
    ("not_found", {}, "No Steam Store response wrapper found"),
    ("transport_error", {}, "Steam Store transport error"),
    ("transport_error", {"error": "x" * 1001}, "x" * 1000),
    ("ok", {"body": {}}, "ok envelope did not yield a parsable game"),
    ("unknown", {}, "Steam Store outcome: unknown"),
])
def test_exact_file_mark_arguments(monkeypatch, outcome, changes, message):
    mark = MagicMock()
    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", mark)
    expected_outcome = "refused" if outcome == "ok" else outcome
    assert run_file(monkeypatch, envelope(outcome, **changes)) == expected_outcome
    mark.assert_called_once_with(
        appid=100, outcome=expected_outcome, error_message=message,
        fetched_at=FETCHED_AT, is_replay=True,
    )


def test_preparation_is_pure_and_keeps_redirect_identities():
    payload = envelope("redirected")
    before = copy.deepcopy(payload)
    prepared = _prepare_steam_store_load(payload, Path("bronze.json"))
    assert payload == before
    assert prepared.record["game"]["appid"] == 80
    assert prepared.mark == {
        "appid": 100, "outcome": "redirected", "redirect_to": 90,
        "error_message": "Steam Store redirected appid 100 to 90",
        "fetched_at": FETCHED_AT, "is_replay": True,
    }


@pytest.mark.parametrize("payload, error", [
    (envelope("transport_error", error=123), TypeError),
    (envelope("ok", body=[1]), AttributeError),
    ({"envelope": ENVELOPE_VERSION}, KeyError),
    ({"envelope": "unsupported"}, ValueError),
])
def test_native_errors_before_effects(monkeypatch, payload, error):
    connection = MagicMock()
    mark = MagicMock()
    monkeypatch.setattr(load, "get_db_connection", connection)
    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", mark)
    with pytest.raises(error):
        run_file(monkeypatch, payload)
    connection.assert_not_called()
    mark.assert_not_called()


def test_legacy_invalid_body_exact_error(monkeypatch):
    with pytest.raises(ValueError) as caught:
        run_file(monkeypatch, {"100": {"success": False}})
    assert str(caught.value) == (
        "Legacy Steam Store file bronze.json was read as outcome 'ok' "
        "(the unconditional legacy fallback) but its body did not yield a parsable "
        "game -- most likely an embedded success: false that the legacy shape "
        "cannot distinguish from a real ok. Refusing to silently drop it."
    )


def seed_requested():
    with get_db_connection() as connection:
        connection.execute("INSERT INTO games (appid, name) VALUES (100, 'requested')")


def stored_rows():
    with get_db_connection() as connection:
        return connection.execute(
            "SELECT appid, name, steam_store_outcome, steam_store_redirect_to, "
            "steam_store_attempts, steam_store_errors FROM games ORDER BY appid"
        ).fetchall()


@pytest.mark.parametrize("outcome, changes, expected", [
    ("not_found", {}, ("not_found", 1, 0)),
    ("transport_error", {"error": "offline"}, ("transport_error", 0, 1)),
    ("ok", {"body": {}}, ("refused", 1, 0)),
])
def test_database_counters_and_replay(test_database, monkeypatch, outcome, changes, expected):
    seed_requested()
    payload = envelope(outcome, **changes)
    expected_outcome, attempts, errors = expected
    assert run_file(monkeypatch, payload) == expected_outcome
    first = stored_rows()
    assert first == [(100, "requested", expected_outcome, None, attempts, errors)]
    assert run_file(monkeypatch, payload) == expected_outcome
    assert stored_rows() == first


def test_redirect_commits_target_before_mark_failure(test_database, monkeypatch):
    seed_requested()

    def fail_mark(**kwargs):
        assert stored_rows() == [
            (80, "target", "ok", None, 1, 0),
            (100, "requested", None, None, 0, 0),
        ]
        raise RuntimeError("mark failed")

    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", fail_mark)
    with pytest.raises(RuntimeError, match="mark failed"):
        run_file(monkeypatch, envelope("redirected"))
    assert stored_rows()[0] == (80, "target", "ok", None, 1, 0)


def test_redirect_target_failure_rolls_back_and_suppresses_mark(test_database, monkeypatch):
    seed_requested()
    original = load.load_transformed_record
    mark = MagicMock()

    def fail_after_write(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("target failed")

    monkeypatch.setattr(load, "load_transformed_record", fail_after_write)
    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", mark)
    with pytest.raises(RuntimeError, match="target failed"):
        run_file(monkeypatch, envelope("redirected"))
    mark.assert_not_called()
    assert stored_rows() == [(100, "requested", None, None, 0, 0)]


def test_redirect_database_identity_and_replay(test_database, monkeypatch):
    seed_requested()
    payload = envelope("redirected")
    assert run_file(monkeypatch, payload) == "redirected"
    first = stored_rows()
    assert first == [
        (80, "target", "ok", None, 1, 0),
        (100, "requested", "redirected", 90, 1, 0),
    ]
    assert run_file(monkeypatch, payload) == "redirected"
    assert stored_rows() == first


def test_empty_redirect_marks_without_target_connection(monkeypatch):
    connection = MagicMock()
    mark = MagicMock()
    monkeypatch.setattr(load, "get_db_connection", connection)
    monkeypatch.setattr(load, "mark_steam_store_enrichment_result", mark)
    assert run_file(monkeypatch, envelope("redirected", body={})) == "redirected"
    connection.assert_not_called()
    mark.assert_called_once_with(
        appid=100, outcome="redirected", redirect_to=90,
        error_message="Steam Store redirected appid 100 to 90",
        fetched_at=FETCHED_AT, is_replay=True,
    )


def test_redirect_diagnostic_is_not_truncated():
    redirect_to = "9" * 1001
    prepared = _prepare_steam_store_load(
        envelope("redirected", redirect_to=redirect_to), Path("bronze.json")
    )
    assert prepared.mark["error_message"] == f"Steam Store redirected appid 100 to {redirect_to}"


def test_missing_appid_and_unknown_outcome(monkeypatch):
    payload = envelope("redirected", body=[1])
    del payload["appid"]
    assert run_file(monkeypatch, payload) == "redirected"
    with pytest.raises(ValueError, match="does not accept"):
        run_file(monkeypatch, envelope("unknown"))


def test_answer_resets_transport_errors(test_database, monkeypatch):
    seed_requested()
    assert run_file(monkeypatch, envelope("transport_error")) == "transport_error"
    assert stored_rows() == [(100, "requested", "transport_error", None, 0, 1)]
    payload = envelope("not_found", fetched_at="2026-08-13T12:00:00+00:00")
    assert run_file(monkeypatch, payload) == "not_found"
    assert stored_rows() == [(100, "requested", "not_found", None, 1, 0)]
    assert run_file(monkeypatch, payload) == "not_found"
    assert stored_rows() == [(100, "requested", "not_found", None, 1, 0)]
