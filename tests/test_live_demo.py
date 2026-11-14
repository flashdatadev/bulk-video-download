import json

import httpx
import pytest
from flashdata import FlashData

from bulk_video_download.demo import DemoTransport
from bulk_video_download.live_demo import DEMO_IDS, DEMO_OPTIONS, run_live_demo

STORAGE = {
    "storage_type": "s3",
    "storage_url": "test-bucket",
    "region": "us-east-1",
    "access_key": "test-key",
    "secret_key": "test-secret",
}


def test_live_demo_request_settings_and_rerun_use_real_sdk_offline(tmp_path, monkeypatch):
    # Exercise the production path without making live calls in automated tests.
    monkeypatch.setattr("bulk_video_download.demo.DEMO_IDS", list(DEMO_IDS))
    transport = DemoTransport()
    run = tmp_path / "run"
    with FlashData(api_key="test-key", transport=httpx.MockTransport(transport.handle)) as client:
        result = run_live_demo(client, STORAGE, run)
        before = len(transport.requests)
        assert run_live_demo(client, STORAGE, run) == result
        assert len(transport.requests) == before
    creates = [r for r in transport.requests if r.url.path == "/v2/bulk-jobs"]
    assert len(creates) == 1
    options = json.loads(creates[0].content)["options"]
    assert all(options[key] == value for key, value in DEMO_OPTIONS.items())
    uploaded = next(r for r in transport.requests if r.method == "PUT")
    assert uploaded.content.decode().splitlines() == list(DEMO_IDS)
    assert result["rows"] == 3
    assert "test-secret" not in (run / "run.json").read_text()


def test_existing_unknown_run_cannot_trigger_a_new_demo(tmp_path):
    transport = DemoTransport()
    run = tmp_path / "run"
    run.mkdir()
    with FlashData(api_key="test-key", transport=httpx.MockTransport(transport.handle)) as client:
        with pytest.raises((ValueError, OSError)):
            run_live_demo(client, STORAGE, run)
    assert not transport.requests
