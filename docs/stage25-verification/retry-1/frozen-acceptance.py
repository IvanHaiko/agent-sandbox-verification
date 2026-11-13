"""Blind acceptance. Run later with REQUIRE_DB_TESTS=1 pytest -q this_file.
Only public loader/transform calls and real PostgreSQL are used.
"""
import copy
import json
import threading
import time
from datetime import datetime, timezone

import psycopg
import pytest
from psycopg.rows import dict_row


def _connection():
    from src.db import get_db_connection
    return get_db_connection()


def _observation(stamp, games, metadata=True):
    streams = []
    for number, (game, viewers) in enumerate(games, 1):
        streams.append({
            "id": str(100000 + number), "user_id": str(200000 + number),
            "user_login": "acceptance_user_" + str(number),
            "user_name": "Acceptance User " + str(number),
            "game_id": game, "game_name": "Game " + game,
            "type": "live", "title": "Acceptance stream", "viewer_count": viewers,
            "started_at": "2025-01-14T12:00:00Z", "language": "en",
            "thumbnail_url": "https://example.invalid/{width}x{height}",
            "tag_ids": [], "tags": [], "is_mature": False,
        })
    raw = {"fetched_at": stamp, "data": streams}
    if metadata:
        raw.update(source="twitch", request="streams", stream_count=len(streams))
    return raw


def _write(tmp_path, raw, name="observation.json"):
    path = tmp_path / name
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def _load(tmp_path, raw, name="observation.json"):
    from src.load import load_twitch_file
    return load_twitch_file(_write(tmp_path, raw, name))


def _rows():
    with _connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM twitch_game_snapshots ORDER BY sample_hour, twitch_game_id")
            return cursor.fetchall()


def _metric(row, names):
    # Physical metric spelling is discovered at execution, without reading schema.
    found = [name for name in names if name in row]
    assert found, f"No persisted metric among {names}; columns: {tuple(row)}"
    values = [row[name] for name in found]
    assert all(value == values[0] for value in values)
    return values[0]


def _assert_observation(rows, expected, stamp):
    instant = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    if instant.tzinfo is not None:
        instant = instant.astimezone(timezone.utc).replace(tzinfo=None)
    hour = instant.replace(minute=0, second=0, microsecond=0)
    assert len(rows) == len(expected)
    assert {str(row["twitch_game_id"]) for row in rows} == set(expected)
    for row in rows:
        game = str(row["twitch_game_id"])
        viewers, streams = expected[game]
        assert _metric(row, ("viewer_count", "total_viewers", "viewers")) == viewers
        assert _metric(row, ("stream_count", "total_streams", "streams")) == streams
        assert row["sample_hour"] == hour
        assert row["sample_time"] == instant
        assert row["sample_time_source"] == "bronze"
        assert row["snapshot_time"] is not None


def test_initial_load_and_public_time_semantics(test_database, tmp_path):
    from src.transform import parse_twitch_fetched_at, transform_twitch_streams
    raw = _observation("2025-01-14T16:10:03+02:00", [("101", 60), ("101", 40), ("202", 7)])
    assert parse_twitch_fetched_at(raw) == datetime(2025, 1, 14, 14, 10, 3)
    legacy = _observation("2025-01-14T14:10:03", [("101", 1)], metadata=False)
    assert parse_twitch_fetched_at(legacy) == datetime(2025, 1, 14, 14, 10, 3)
    transformed = transform_twitch_streams(raw)
    assert isinstance(transformed, list) and len(transformed) == 2
    assert _load(tmp_path, raw) == 2
    _assert_observation(_rows(), {"101": (100, 2), "202": (7, 1)}, raw["fetched_at"])


def test_identical_replay_has_no_persisted_writes(test_database, tmp_path):
    raw = _observation("2025-01-14T14:10:00Z", [("101", 100), ("202", 200)], metadata=False)
    assert _load(tmp_path, raw) == 2
    before = _rows()
    # xmin detects an UPDATE even when ordinary column values stay equal.
    with _connection() as connection:
        versions = connection.execute(
            "SELECT twitch_game_id, xmin::text FROM twitch_game_snapshots ORDER BY twitch_game_id"
        ).fetchall()
    assert _load(tmp_path, raw) == 2
    assert _rows() == before
    with _connection() as connection:
        assert connection.execute(
            "SELECT twitch_game_id, xmin::text FROM twitch_game_snapshots ORDER BY twitch_game_id"
        ).fetchall() == versions


def test_same_hour_replaces_membership_and_preserves_retained_identity(test_database, tmp_path):
    first = _observation("2025-01-14T14:10:00Z", [("101", 100), ("202", 200), ("303", 300)])
    second = _observation("2025-01-14T14:45:00Z", [("101", 70), ("101", 80), ("303", 350), ("404", 400)])
    assert _load(tmp_path, first) == 3
    before = {str(row["twitch_game_id"]): row for row in _rows()}
    assert _load(tmp_path, second) == 3
    after = _rows()
    _assert_observation(after, {"101": (150, 2), "303": (350, 1), "404": (400, 1)}, second["fetched_at"])
    for row in after:
        game = str(row["twitch_game_id"])
        if game in before:
            assert row["id"] == before[game]["id"]
            assert row["snapshot_time"] == before[game]["snapshot_time"]


def test_replacement_database_failure_rolls_back_complete_observation(test_database, tmp_path):
    first = _observation("2025-01-14T14:10:00Z", [("101", 100), ("202", 200), ("303", 300)])
    replacement = _observation("2025-01-14T14:45:00Z", [("101", 150), ("404", 400), ("505", 500)])
    _load(tmp_path, first)
    before = _rows()
    with _connection() as connection:
        connection.execute("CREATE SEQUENCE acceptance_write_attempt")
        connection.execute("""
            CREATE FUNCTION acceptance_fail_second_write() RETURNS trigger
            LANGUAGE plpgsql AS $$
            BEGIN
              IF nextval('acceptance_write_attempt') = 2 THEN
                RAISE EXCEPTION 'acceptance deliberate second-row write failure';
              END IF;
              RETURN NEW;
            END $$
        """)
        connection.execute("""
            CREATE TRIGGER acceptance_write_failure
            AFTER INSERT OR UPDATE ON twitch_game_snapshots
            FOR EACH ROW EXECUTE FUNCTION acceptance_fail_second_write()
        """)
        connection.commit()
    try:
        try:
            result = _load(tmp_path, replacement)
        except psycopg.Error as exc:
            assert "acceptance deliberate second-row write failure" in str(exc)
        else:
            assert result == 0, "A failed replacement cannot report accepted aggregates"
        with _connection() as connection:
            assert connection.execute("SELECT last_value FROM acceptance_write_attempt").fetchone()[0] == 2
        assert _rows() == before
    finally:
        with _connection() as connection:
            connection.execute("DROP TRIGGER acceptance_write_failure ON twitch_game_snapshots")
            connection.execute("DROP FUNCTION acceptance_fail_second_write()")
            connection.execute("DROP SEQUENCE acceptance_write_attempt")
            connection.commit()
    assert _load(tmp_path, replacement) == 3
    _assert_observation(_rows(), {"101": (150, 1), "404": (400, 1), "505": (500, 1)}, replacement["fetched_at"])


def test_other_hours_are_completely_unchanged(test_database, tmp_path):
    earlier = _observation("2025-01-14T13:59:59Z", [("101", 11), ("202", 22)])
    later = _observation("2025-01-14T15:00:00Z", [("101", 33), ("505", 55)])
    _load(tmp_path, earlier)
    _load(tmp_path, later)
    unaffected = _rows()
    _load(tmp_path, _observation("2025-01-14T14:01:00Z", [("202", 99)]))
    newest = _observation("2025-01-14T14:59:59Z", [("101", 44), ("404", 66)])
    assert _load(tmp_path, newest) == 2
    rows = _rows()
    target = [row for row in rows if row["sample_hour"] == datetime(2025, 1, 14, 14)]
    assert [row for row in rows if row not in target] == unaffected
    _assert_observation(target, {"101": (44, 1), "404": (66, 1)}, newest["fetched_at"])


def test_stale_ordering_equal_conflict_and_equivalent_offsets(test_database, tmp_path):
    newest = _observation("2025-01-14T14:45:00Z", [("101", 150), ("303", 350)])
    assert _load(tmp_path, newest) == 2
    before = _rows()
    stale = _observation("2025-01-14T16:10:00+02:00", [("101", 100), ("202", 200)])
    assert _load(tmp_path, stale) == 0
    assert _rows() == before
    equivalent = copy.deepcopy(newest)
    equivalent["fetched_at"] = "2025-01-14T16:45:00+02:00"
    equivalent["data"].reverse()
    assert _load(tmp_path, equivalent) == 2
    assert _rows() == before
    conflict = _observation(newest["fetched_at"], [("101", 999), ("404", 1)])
    with pytest.raises(ValueError):
        _load(tmp_path, conflict)
    assert _rows() == before


def test_historical_load_clock_does_not_block_bronze(test_database, tmp_path):
    _load(tmp_path, _observation("2025-01-14T14:50:00Z", [("101", 1), ("202", 2)]))
    with _connection() as connection:
        connection.execute("UPDATE twitch_game_snapshots SET sample_time_source = 'load_clock'")
        connection.commit()
    incoming = _observation("2025-01-14T14:10:00Z", [("101", 77), ("303", 88)])
    assert _load(tmp_path, incoming) == 2
    _assert_observation(_rows(), {"101": (77, 1), "303": (88, 1)}, incoming["fetched_at"])


_INVALID = (
    "empty", "missing_data", "not_list", "bad_time", "missing_time",
    "incomplete", "complete_false", "success_false", "error", "failure",
    "wrong_source", "wrong_request", "wrong_count", "string_count", "bool_count",
    "malformed_record", "missing_viewers", "bad_viewers", "only_blank_category",
)


@pytest.mark.parametrize("kind", _INVALID)
def test_invalid_or_incomplete_observation_preserves_previous_hour(test_database, tmp_path, kind):
    original = _observation("2025-01-14T14:10:00Z", [("101", 100), ("202", 200)])
    _load(tmp_path, original)
    before = _rows()
    incoming = _observation("2025-01-14T14:45:00Z", [("303", 300)])
    if kind == "empty":
        incoming.update(data=[], stream_count=0)
    elif kind == "missing_data":
        del incoming["data"]
    elif kind == "not_list":
        incoming["data"] = {"game_id": "303"}
    elif kind == "bad_time":
        incoming["fetched_at"] = "not-a-date"
    elif kind == "missing_time":
        del incoming["fetched_at"]
    elif kind == "incomplete":
        incoming["incomplete"] = True
    elif kind in ("complete_false", "success_false"):
        incoming[kind.split("_")[0]] = False
    elif kind in ("error", "failure"):
        incoming[kind] = "upstream request failed"
    elif kind == "wrong_source":
        incoming["source"] = "steam"
    elif kind == "wrong_request":
        incoming["request"] = "games"
    elif kind == "wrong_count":
        incoming["stream_count"] = 2
    elif kind == "string_count":
        incoming["stream_count"] = "1"
    elif kind == "bool_count":
        incoming["stream_count"] = True
    elif kind == "malformed_record":
        incoming["data"].append(None)
        incoming["stream_count"] = 2
    elif kind == "missing_viewers":
        del incoming["data"][0]["viewer_count"]
    elif kind == "bad_viewers":
        incoming["data"][0]["viewer_count"] = "many"
    elif kind == "only_blank_category":
        incoming["data"][0].update(game_id="", game_name="")
    try:
        result = _load(tmp_path, incoming)
    except (ValueError, TypeError, KeyError):
        pass
    else:
        assert result == 0, "Rejected observations must not report accepted aggregates"
    assert _rows() == before


def test_valid_unassigned_category_is_filtered(test_database, tmp_path):
    raw = _observation("2025-01-14T14:10:00Z", [("101", 10), ("", 999)])
    raw["data"][1]["game_name"] = ""
    assert _load(tmp_path, raw) == 1
    _assert_observation(_rows(), {"101": (10, 1)}, raw["fetched_at"])


@pytest.mark.parametrize("preexisting", [False, True])
def test_concurrent_same_hour_is_one_complete_newest_observation(test_database, tmp_path, monkeypatch, preexisting):
    from src.load import load_twitch_file
    if preexisting:
        _load(tmp_path, _observation("2025-01-14T14:01:00Z", [("606", 6), ("101", 1)]))
    old = _observation("2025-01-14T14:10:00Z", [("101", 100), ("202", 200)])
    new = _observation("2025-01-14T14:45:00Z", [("101", 150), ("303", 350)])
    paths = [_write(tmp_path, old, "old.json"), _write(tmp_path, new, "new.json")]
    barrier = threading.Barrier(3, timeout=5)
    real_connect = psycopg.connect
    results, errors = {}, {}
    worker_names = {"acceptance_old", "acceptance_new"}

    def bounded_connect(*args, **kwargs):
        # Delegate to real psycopg; only tag and bound worker connections.
        name = threading.current_thread().name
        if name in worker_names:
            kwargs["application_name"] = name
            kwargs["connect_timeout"] = 5
            kwargs["options"] = (kwargs.get("options", "") +
                                 " -c statement_timeout=12000 -c lock_timeout=10000")
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(psycopg, "connect", bounded_connect)

    def worker(index):
        try:
            barrier.wait()
            results[index] = load_twitch_file(paths[index])
        except BaseException as exc:
            errors[index] = exc

    threads = [threading.Thread(target=worker, args=(index,), name=name, daemon=True)
               for index, name in enumerate(("acceptance_old", "acceptance_new"))]
    gate = _connection()
    observed_overlap = False
    try:
        gate.execute("LOCK TABLE twitch_game_snapshots IN ACCESS EXCLUSIVE MODE")
        for thread in threads:
            thread.start()
        barrier.wait()
        with _connection() as observer:
            observer.autocommit = True
            deadline = time.monotonic() + 7
            while time.monotonic() < deadline:
                waiting = observer.execute("""
                    SELECT application_name FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND application_name IN ('acceptance_old', 'acceptance_new')
                      AND state = 'active' AND wait_event_type = 'Lock'
                """).fetchall()
                if {row[0] for row in waiting} == worker_names:
                    observed_overlap = True
                    break
                if errors:
                    break
                time.sleep(0.025)
    finally:
        gate.rollback()
        gate.close()
        deadline = time.monotonic() + 16
        for thread in threads:
            if thread.ident is not None:
                thread.join(max(0, deadline - time.monotonic()))
        # Clean up only tagged test workers if an implementation hangs.
        if any(thread.is_alive() for thread in threads):
            with _connection() as connection:
                connection.execute("""
                    SELECT pg_terminate_backend(pid) FROM pg_stat_activity
                    WHERE datname = current_database()
                      AND application_name IN ('acceptance_old', 'acceptance_new')
                """)
                connection.commit()
            for thread in threads:
                if thread.ident is not None:
                    thread.join(2)
    assert not any(thread.is_alive() for thread in threads), "Concurrent loads exceeded bounded deadline"
    assert observed_overlap, "Both loader sessions must demonstrably overlap at real database locks"
    assert not errors, repr(errors)
    assert results[1] == 2
    assert results[0] in (0, 2)
    _assert_observation(_rows(), {"101": (150, 1), "303": (350, 1)}, new["fetched_at"])
    assert _load(tmp_path, old) == 0
    _assert_observation(_rows(), {"101": (150, 1), "303": (350, 1)}, new["fetched_at"])
