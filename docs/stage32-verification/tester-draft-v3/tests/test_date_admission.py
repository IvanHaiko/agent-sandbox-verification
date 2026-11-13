"""Black-box acceptance for UTC collection-pass admission."""

import gzip
import json

import pytest

from collector.manifest import LEGS, empty, load_or_empty, save
from collector.paths import manifest_path
from collector.run import collect
from tests.conftest import FakeHttp, MODELS_URL, RANKINGS_URL


DAY = "2026-08-29"


def utc(day, time="12:00:00"):
    return lambda: f"{day}T{time}Z"


def tree(root):
    """Include empty directories as well as every file's exact bytes."""
    return {
        str(p.relative_to(root)): None if p.is_dir() else p.read_bytes()
        for p in root.rglob("*")
    }


def reject_unchanged(root, day, now):
    before = tree(root)
    http = FakeHttp()
    with pytest.raises(ValueError) as error:
        collect(root, snapshot_date=day, http=http, now=now)
    assert str(error.value).strip(), "Date rejection must explain the error"
    assert any(word in str(error.value).lower() for word in ("date", "day", "utc")), \
        "Error must describe the date-admission problem"
    assert http.call_count == 0
    assert not http.calls
    assert tree(root) == before


@pytest.mark.parametrize("day", ["2026-08-28", "2026-08-30", "2025-12-31", "2027-01-01"])
def test_absent_off_date_is_rejected_without_creating_anything(tmp_path, day):
    reject_unchanged(tmp_path, day, utc(DAY))


@pytest.mark.parametrize("today", ["2026-08-28", "2026-08-30"])
def test_pending_off_date_is_rejected_without_rewriting(tmp_path, today):
    save(manifest_path(tmp_path, DAY), empty(DAY))
    reject_unchanged(tmp_path, DAY, utc(today))


@pytest.mark.parametrize("failed_url", [MODELS_URL, RANKINGS_URL])
@pytest.mark.parametrize("today", ["2026-08-28", "2026-08-30"])
def test_partial_off_date_is_rejected_with_raw_and_history_intact(tmp_path, clock, failed_url, today):
    http = FakeHttp()
    http.fail_urls = {failed_url: 503}
    collect(tmp_path, snapshot_date=DAY, http=http, now=clock)
    assert http.call_count > 0
    reject_unchanged(tmp_path, DAY, utc(today))


def omit_leg(value, leg):
    """Remove a public leg identifier without assuming where legs are nested."""
    if isinstance(value, dict):
        return {key: omit_leg(item, leg) for key, item in value.items() if key != leg}
    if isinstance(value, list):
        return [omit_leg(item, leg) for item in value]
    return value


@pytest.mark.parametrize("complete", [False, True])
def test_legacy_absent_leg_keeps_historical_admission_semantics(tmp_path, clock, complete):
    path = manifest_path(tmp_path, DAY)
    if complete:
        collect(tmp_path, snapshot_date=DAY, http=FakeHttp(), now=clock)
    else:
        save(path, empty(DAY))
    original = json.loads(path.read_text())
    # Exercise each public leg, including whichever legs were added most recently.
    for leg in LEGS:
        legacy = omit_leg(original, leg)
        assert legacy != original, "Fixture must actually omit a leg"
        save(path, legacy)
        if complete:
            before = tree(tmp_path)
            http = FakeHttp()
            expected = load_or_empty(path, DAY)
            result = collect(tmp_path, snapshot_date=DAY, http=http, now=utc("2026-08-30"))
            assert result == expected
            assert http.call_count == 0
            assert not http.calls
            assert tree(tmp_path) == before
        else:
            reject_unchanged(tmp_path, DAY, utc("2026-08-30"))


def test_complete_historical_and_future_partitions_remain_exact_noops(tmp_path, clock):
    expected = collect(tmp_path, snapshot_date=DAY, http=FakeHttp(), now=clock)
    before = tree(tmp_path)
    for today in ("2026-08-28", "2026-08-29", "2026-08-30"):
        http = FakeHttp()
        assert collect(tmp_path, snapshot_date=DAY, http=http, now=utc(today)) == expected
        assert http.call_count == 0
        assert not http.calls
        assert tree(tmp_path) == before


def hf_successes(root):
    """Read documented JSONL envelopes, independent of raw file naming."""
    rows = {}
    for path in root.rglob("*.gz"):
        for line in gzip.decompress(path.read_bytes()).splitlines():
            try:
                row = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(row, dict) and "hf_id" in row and row.get("http_status") == 200:
                assert row["hf_id"] not in rows
                rows[row["hf_id"]] = (row, line)
    return rows


def test_same_day_retry_preserves_successful_hf_observations(tmp_path, clock):
    reference = tmp_path / "reference"
    collect(reference, snapshot_date=DAY, http=FakeHttp(), now=clock)
    reference_rows = hf_successes(reference)
    assert len(reference_rows) >= 2, "Need both failed and successful HF observations"
    failed_repo = sorted(reference_rows)[0]
    root = tmp_path / "retry"
    first = FakeHttp()
    first.hf_status[failed_repo] = 503
    collect(root, snapshot_date=DAY, http=first, now=utc(DAY, "01:00:00"))
    successes = hf_successes(root)
    assert successes
    assert failed_repo not in successes
    # Stored successful legs are immutable; a partial HF aggregate may grow.
    manifest = json.loads(manifest_path(root, DAY).read_text())
    completed_files = {
        manifest_path(root, DAY).parent / state["file"]:
            (manifest_path(root, DAY).parent / state["file"]).read_bytes()
        for state in manifest["legs"].values()
        if state["status"] == "ok" and state.get("file")
    }
    second = FakeHttp()
    result = collect(root, snapshot_date=DAY, http=second, now=utc(DAY, "23:00:00"))
    assert second.call_count > 0
    assert MODELS_URL not in repr(second.calls)
    assert RANKINGS_URL not in repr(second.calls)
    after = hf_successes(root)
    assert set(after) == set(reference_rows)
    for repo, observation in successes.items():
        assert after[repo] == observation, "Retry replaced an earlier successful raw envelope"
    for path, data in completed_files.items():
        assert path.read_bytes() == data, "Retry changed a completed leg's stored bytes"
    before = tree(root)
    third = FakeHttp()
    assert collect(root, snapshot_date=DAY, http=third, now=utc(DAY, "23:59:00")) == result
    assert third.call_count == 0
    assert not third.calls
    assert tree(root) == before


def test_default_partition_uses_utc_today(tmp_path, clock, monkeypatch):
    monkeypatch.setattr("collector.run.utc_today", lambda: DAY)
    first = FakeHttp()
    result = collect(tmp_path, http=first, now=clock)
    assert first.call_count > 0
    assert manifest_path(tmp_path, DAY).is_file()
    before = tree(tmp_path)
    second = FakeHttp()
    assert collect(tmp_path, snapshot_date=DAY, http=second, now=clock) == result
    assert second.call_count == 0
    assert tree(tmp_path) == before
