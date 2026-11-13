"""Unit validation and real PostgreSQL tests (database execution is Controller-only)."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Event
from time import monotonic, sleep

import psycopg
import pytest

from src import load
from src.db import get_db_connection
from src.transform import parse_twitch_fetched_at, transform_twitch_streams


def observation(time="2026-05-13T14:10:00+00:00", games=("A", "B", "C")):
    return {
        "source": "twitch", "request": "streams", "fetched_at": time,
        "stream_count": len(games),
        "data": [
            {"game_id": game, "game_name": game, "viewer_count": 100 + i}
            for i, game in enumerate(games)
        ],
    }


def save(tmp_path, payload, name="streams.json"):
    path = tmp_path / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def stored():
    with get_db_connection() as connection:
        return connection.execute(
            "SELECT id, twitch_game_id, twitch_game_name, viewer_count, stream_count, "
            "sample_time, sample_hour, sample_time_source, snapshot_time "
            "FROM twitch_game_snapshots ORDER BY sample_hour, twitch_game_id"
        ).fetchall()


@pytest.mark.parametrize("change", [
    {"data": None}, {"data": {}}, {"data": []}, {"data": [None]},
    {"stream_count": True}, {"stream_count": 2}, {"source": "other"},
    {"request": "games"}, {"complete": False}, {"incomplete": True},
    {"success": False}, {"error": "API failed"}, {"failure": True},
    {"outcome": "transport_error"}, {"fetched_at": None},
    {"fetched_at": "2026-05-13"}, {"fetched_at": "invalid"},
    {"data": [{"game_id": "A", "game_name": "A", "viewer_count": -1}]},
    {"data": [{"game_id": "A", "game_name": "A", "viewer_count": 1.5}]},
    {"data": [{"game_id": "A", "game_name": "A", "viewer_count": True}]},
    {"data": [{"game_id": "A", "game_name": "A"}]},
    {"data": [{"game_name": "A", "viewer_count": 1}]},
    {"data": [{"game_id": "A", "viewer_count": 1}]},
    {"data": [{"game_id": "", "game_name": "", "viewer_count": 1}]},
])
def test_invalid_input_never_connects(monkeypatch, tmp_path, change):
    payload = observation(games=("A",))
    payload.update(change)

    def forbidden_connection():
        pytest.fail("Invalid observation opened a database connection")

    monkeypatch.setattr(load, "get_db_connection", forbidden_connection)
    with pytest.raises(ValueError):
        load.load_twitch_file(save(tmp_path, payload))


@pytest.mark.parametrize("payload", [[], None, {}, {"fetched_at": "2026-05-13T14:10:00"}])
def test_invalid_shape(payload):
    with pytest.raises(ValueError):
        transform_twitch_streams(payload)


def test_legacy_and_unassigned_streams():
    payload = observation(games=("A",))
    for key in ("source", "request", "stream_count"):
        del payload[key]
    payload["data"].append({"game_id": "", "game_name": "", "viewer_count": 9})
    payload["data"][0]["viewer_count"] = "12"
    rows = transform_twitch_streams(payload)
    assert len(rows) == 1
    assert rows[0]["viewer_count"] == 12
    assert rows[0]["stream_count"] == 1


def test_timestamp_normalization():
    expected = datetime(2026, 5, 13, 14, 10)
    for time in ("2026-05-13T16:10:00+02:00", "2026-05-13T14:10:00Z",
                 "2026-05-13T14:10:00"):
        assert parse_twitch_fetched_at({"fetched_at": time}) == expected


def test_db_membership_replay_order_and_hour_isolation(test_database, tmp_path):
    first = save(tmp_path, observation(), "first.json")
    assert load.load_twitch_file(first) == 3
    original = stored()
    assert {row[1] for row in original} == {"A", "B", "C"}
    assert all(row[5] == datetime(2026, 5, 13, 14, 10) for row in original)
    assert all(row[7] == "bronze" for row in original)
    assert load.load_twitch_file(first) == 3
    assert stored() == original

    other = save(tmp_path, observation("2026-05-13T15:10:00Z", ("E",)), "other.json")
    load.load_twitch_file(other)
    other_rows = [row for row in stored() if row[6].hour == 15]
    second = save(tmp_path, observation("2026-05-13T16:45:00+02:00", ("A", "C", "D")), "second.json")
    assert load.load_twitch_file(second) == 3
    replacement = stored()
    hour = [row for row in replacement if row[6].hour == 14]
    assert {row[1] for row in hour} == {"A", "C", "D"}
    assert {row[1]: row[3] for row in hour} == {"A": 100, "C": 101, "D": 102}
    assert all(row[5] == datetime(2026, 5, 13, 14, 45) for row in hour)
    for row in hour:
        old = next((old for old in original if old[1] == row[1]), None)
        if old:
            assert (row[0], row[8]) == (old[0], old[8])
    assert [row for row in replacement if row[6].hour == 15] == other_rows
    assert load.load_twitch_file(first) == 0
    assert stored() == replacement
    conflict = save(tmp_path, observation("2026-05-13T14:45:00Z", ("X",)), "conflict.json")
    with pytest.raises(ValueError, match="equal fetched_at"):
        load.load_twitch_file(conflict)
    assert stored() == replacement


def test_db_insertion_failure_rolls_back(test_database, tmp_path, monkeypatch):
    load.load_twitch_file(save(tmp_path, observation()))
    original = stored()
    insert = load.insert_twitch_game_snapshot
    calls = 0

    def fail_second(connection, snapshot):
        nonlocal calls
        calls += 1
        if calls == 2:
            # Real SQL failure after the first upsert, not only a Python exception.
            connection.execute("SELECT 1 / 0")
        insert(connection, snapshot)

    monkeypatch.setattr(load, "insert_twitch_game_snapshot", fail_second)
    with pytest.raises(psycopg.errors.DivisionByZero):
        load.load_twitch_file(save(tmp_path, observation("2026-05-13T14:45:00Z", ("D", "A"))))
    assert calls == 2
    assert stored() == original


def test_db_historical_provenance_and_unknown_bronze_time(test_database, tmp_path):
    with get_db_connection() as connection:
        connection.execute(
            "INSERT INTO twitch_game_snapshots (twitch_game_id, twitch_game_name, "
            "viewer_count, stream_count, sample_time, sample_hour, sample_time_source) "
            "VALUES ('old', 'old', 1, 1, '2026-05-13 14:59', '2026-05-13 14:00', 'load_clock')"
        )
    path = save(tmp_path, observation())
    assert load.load_twitch_file(path) == 3
    assert {row[1] for row in stored()} == {"A", "B", "C"}
    with get_db_connection() as connection:
        connection.execute("UPDATE twitch_game_snapshots SET sample_time = NULL WHERE twitch_game_id = 'A'")
    original = stored()
    with pytest.raises(ValueError, match="unknown observation times"):
        load.load_twitch_file(save(tmp_path, observation("2026-05-13T14:45:00Z")))
    assert stored() == original


@pytest.mark.parametrize("first_is_newer", [False, True])
@pytest.mark.parametrize("seed_hour", [False, True])
def test_db_concurrent_same_hour(test_database, tmp_path, monkeypatch, first_is_newer, seed_hour):
    if seed_hour:
        load.load_twitch_file(save(tmp_path, observation(), "seed.json"))
    older = save(tmp_path, observation("2026-05-13T14:20:00Z", ("A", "X")), "older.json")
    newer = save(tmp_path, observation("2026-05-13T14:45:00Z", ("A", "Y")), "newer.json")
    first, second = (newer, older) if first_is_newer else (older, newer)
    locked, release, second_connected = Event(), Event(), Event()
    insert = load.insert_twitch_game_snapshot
    connect = load.get_db_connection
    second_pid = []
    first_time = parse_twitch_fetched_at(json.loads(first.read_text()))

    def pause_first(connection, snapshot):
        if snapshot["sample_time"] == first_time and not locked.is_set():
            locked.set()
            assert release.wait(10), "Timed out waiting to release first writer"
        insert(connection, snapshot)

    def bounded_connection():
        connection = connect()
        connection.execute("SET statement_timeout = '8s'")
        connection.commit()
        if locked.is_set():
            second_pid.append(connection.info.backend_pid)
            second_connected.set()
        return connection

    monkeypatch.setattr(load, "insert_twitch_game_snapshot", pause_first)
    monkeypatch.setattr(load, "get_db_connection", bounded_connection)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first_future = pool.submit(load.load_twitch_file, first)
        try:
            assert locked.wait(10), "First writer did not acquire serialization"
            second_future = pool.submit(load.load_twitch_file, second)
            assert second_connected.wait(10), "Second writer did not connect"
            # Prove the second transaction is actually waiting on serialization
            # before allowing the first to commit; scheduler overlap alone is weak.
            deadline = monotonic() + 5
            with connect() as observer:
                while monotonic() < deadline:
                    waiting = observer.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_locks WHERE pid = %s "
                        "AND relation = 'twitch_game_snapshots'::regclass "
                        "AND NOT granted)", (second_pid[0],),
                    ).fetchone()[0]
                    if waiting:
                        break
                    sleep(0.01)
                assert waiting, "Second writer never waited on the table lock"
        finally:
            release.set()
        assert first_future.result(timeout=12) == 2
        assert second_future.result(timeout=12) == (0 if first_is_newer else 2)
    rows = stored()
    assert {row[1]: row[3] for row in rows} == {"A": 100, "Y": 101}
    assert all(row[5] == datetime(2026, 5, 13, 14, 45) for row in rows)
