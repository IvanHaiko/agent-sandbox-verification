import json

import pytest
import requests

from src import extract_steam_store, extract_steamspy


class FakeResponse:
    """
    Minimal stand-in for requests.Response, covering only what
    fetch_appdetails reads: .url, .status_code, .text, .json(), and
    .raise_for_status().
    """

    def __init__(
        self,
        status_code=200,
        text="",
        json_data=None,
        json_error=None,
        url="https://store.steampowered.com/api/appdetails?appids=730",
    ):
        self.status_code = status_code
        self.text = text
        self._json_data = json_data
        self._json_error = json_error
        self.url = url

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"{self.status_code} Server Error")

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._json_data


def test_steamspy_build_output_filename_for_all_page():
    file_name = extract_steamspy.build_output_filename(
        request_type="all",
        page=0,
    )

    assert file_name.startswith("page_0_")
    assert file_name.endswith(".json")


def test_steamspy_save_raw_json_uses_partitioned_path(monkeypatch, tmp_path):
    fake_data = {
        "730": {
            "appid": 730,
            "name": "Counter-Strike 2",
        }
    }

    monkeypatch.setattr(extract_steamspy, "RAW_DATA_DIR", tmp_path)

    file_path = extract_steamspy.save_raw_json(
        data=fake_data,
        request_type="all",
        page=0,
    )

    assert file_path.parent.parent.name == "all"
    assert file_path.parent.parent.parent.name == "steamspy"
    assert file_path.name.startswith("page_0_")

    with open(file_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data == fake_data


def test_fetch_appdetails_ok_outcome(monkeypatch):
    body = {
        "730": {
            "success": True,
            "data": {"steam_appid": 730, "name": "Counter-Strike 2"},
        }
    }

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["envelope"] == 1
    assert envelope["outcome"] == "ok"
    assert envelope["appid"] == 730
    assert envelope["http_status"] == 200
    assert envelope["error"] is None
    assert envelope["body"] == body


def test_fetch_appdetails_refused_outcome(monkeypatch):
    """
    success: false is a real Steam Store answer ("this appid says no"),
    not an absence of one -- outcome must be "refused", body kept verbatim.
    """

    body = {"999999": {"success": False}}

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(999999)

    assert envelope["outcome"] == "refused"
    assert envelope["body"] == body
    assert envelope["error"] is None


def test_fetch_appdetails_not_found_outcome(monkeypatch):
    """
    A response with no wrapper for this appid at all is a distinct fact
    from a refusal -- outcome must be "not_found", not "refused".
    """

    body = {}

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(123456)

    assert envelope["outcome"] == "not_found"
    assert envelope["body"] == body


def test_fetch_appdetails_not_found_outcome_for_non_dict_wrapper(monkeypatch):
    """
    A wrapper value that is present but is not a JSON object (e.g. a bare
    string) carries no success/data fields to read. It must be treated
    the same as a missing wrapper ("not_found") and bronze must still be
    written -- not raise AttributeError on app_wrapper.get(...) before
    anything is saved.
    """

    body = {"730": "maintenance"}

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "not_found"
    assert envelope["body"] == body


def test_fetch_appdetails_redirected_outcome(monkeypatch):
    """
    success: true but data.steam_appid names a different appid than the
    one requested is a "redirected" outcome, and the target appid must
    land in a typed field (redirect_to), not folded into prose.
    """

    body = {
        "100": {
            "success": True,
            "data": {
                "steam_appid": 80,
                "name": "Counter-Strike: Condition Zero",
            },
        }
    }

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(100)

    assert envelope["outcome"] == "redirected"
    assert envelope["appid"] == 100
    assert envelope["redirect_to"] == 80
    assert envelope["body"] == body


def test_fetch_appdetails_ok_outcome_has_no_redirect_to(monkeypatch):
    """
    redirect_to must be null whenever the response actually answers for
    the requested appid, so a reader can trust the field without also
    checking outcome first.
    """

    body = {
        "730": {
            "success": True,
            "data": {"steam_appid": 730, "name": "Counter-Strike 2"},
        }
    }

    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text=json.dumps(body), json_data=body)

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "ok"
    assert envelope["redirect_to"] is None


def test_fetch_appdetails_transport_error_on_bad_http_status(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=503, text="Service Unavailable")

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "transport_error"
    assert envelope["http_status"] == 503
    assert envelope["body"] is None
    assert envelope["error"] is not None


def test_fetch_appdetails_transport_error_on_empty_body(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return FakeResponse(status_code=200, text="   ")

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "transport_error"
    assert envelope["body"] is None
    assert "empty" in envelope["error"].lower()


def test_fetch_appdetails_transport_error_on_invalid_json(monkeypatch):
    def fake_get(url, params, headers, timeout):
        return FakeResponse(
            status_code=200,
            text="not json",
            json_error=requests.exceptions.JSONDecodeError("msg", "not json", 0),
        )

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "transport_error"
    assert envelope["body"] is None
    assert "invalid JSON" in envelope["error"]


def test_fetch_appdetails_transport_error_on_network_failure(monkeypatch):
    """
    A timeout or connection failure never produces a response object at
    all -- this is the case the pre-fix code did not classify.
    """

    def fake_get(url, params, headers, timeout):
        raise requests.exceptions.Timeout("Connection timed out")

    monkeypatch.setattr(extract_steam_store.requests, "get", fake_get)

    envelope = extract_steam_store.fetch_appdetails(730)

    assert envelope["outcome"] == "transport_error"
    assert envelope["http_status"] is None
    assert envelope["body"] is None
    assert "timed out" in envelope["error"].lower()


def test_fetch_appdetails_raises_for_non_positive_appid():
    with pytest.raises(ValueError):
        extract_steam_store.fetch_appdetails(0)


def test_steam_store_save_raw_json_writes_envelope_verbatim(monkeypatch, tmp_path):
    """
    save_raw_json must not reshape the envelope it is given -- it is a
    plain writer, whatever outcome the envelope carries.
    """

    envelope = {
        "envelope": 1,
        "source": "steam_store",
        "outcome": "transport_error",
        "appid": 730,
        "request": {"appids": 730},
        "url": None,
        "fetched_at": "2026-08-12T10:00:00+00:00",
        "http_status": None,
        "error": "Connection timed out",
        "body": None,
    }

    monkeypatch.setattr(extract_steam_store, "RAW_DATA_DIR", tmp_path)

    file_path = extract_steam_store.save_raw_json(data=envelope, appid=730)

    with open(file_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data == envelope


def test_steam_store_save_raw_json_uses_partitioned_path(monkeypatch, tmp_path):
    fake_data = {
        "730": {
            "success": True,
            "data": {
                "steam_appid": 730,
                "name": "Counter-Strike 2",
            },
        }
    }

    monkeypatch.setattr(extract_steam_store, "RAW_DATA_DIR", tmp_path)

    file_path = extract_steam_store.save_raw_json(
        data=fake_data,
        appid=730,
    )

    assert file_path.parent.parent.name == "appdetails"
    assert file_path.parent.parent.parent.name == "steam_store"
    assert file_path.name.startswith("730_")

    with open(file_path, "r", encoding="utf-8") as file:
        saved_data = json.load(file)

    assert saved_data == fake_data


def test_transport_error_envelope_carries_no_fetched_at_and_no_body():
    """
    outcome == "transport_error" implies fetched_at IS NULL and body IS
    NULL, in the envelope itself.

    No answer arrived, so there is no moment of receiving one and no
    response to keep. Stamping the attempt clock into fetched_at would
    make the field assert an answer that never came -- the same class of
    fabrication migration 010 undid for Twitch sample_time and 013 for
    is_free. The attempt is timestamped by the file name and, in the
    database, by steam_store_updated_at. This is a checkable consequence
    of that decision rather than an agreement in prose.
    """

    envelope = extract_steam_store.build_envelope(
        appid=730,
        request={"appids": 730},
        url="https://example.invalid/api",
        fetched_at="2026-08-12T10:00:00+00:00",
        outcome="transport_error",
        http_status=503,
        body={"730": {"success": True}},
        error="503 Server Error",
    )

    assert envelope["outcome"] == "transport_error"
    assert envelope["fetched_at"] is None
    assert envelope["body"] is None
    # The failure itself is still described, and the attempt is still
    # attributable to an appid.
    assert envelope["error"] == "503 Server Error"
    assert envelope["appid"] == 730
    assert envelope["http_status"] == 503
