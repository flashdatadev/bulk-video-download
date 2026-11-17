import json

import httpx
import pytest
from flashdata import FlashData

from bulk_video_download import collect, start
from bulk_video_download.demo import DEMO_IDS, DemoTransport


@pytest.mark.parametrize("provider", ["s3", "s3_compatible", "oss", "cos", "bos", "tos"])
def test_sts_storage_reaches_bulk_api_and_stays_out_of_recovery_files(tmp_path, provider):
    storage = {
        "storage_type": provider,
        "storage_url": "test-bucket",
        "access_key": "fixture-temporary-access",
        "secret_key": "fixture-temporary-secret",
        "session_token": "fixture-session-token",
    }
    storage.update(
        {
            "s3": {"region": "us-east-1"},
            "s3_compatible": {"endpoint_url": "https://storage.example.com"},
            "oss": {"endpoint_url": "https://oss-cn-hangzhou.aliyuncs.com"},
            "cos": {"storage_url": "test-bucket-1250000000", "region": "ap-guangzhou"},
            "bos": {"region": "bj"},
            "tos": {"region": "cn-beijing"},
        }[provider]
    )
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(DEMO_IDS), encoding="utf-8")
    run = tmp_path / "run"
    transport = DemoTransport()
    with FlashData(
        api_key="fixture-api-key", transport=httpx.MockTransport(transport.handle)
    ) as client:
        job_id = start(client, ids, run_dir=run, storage=storage)
        summary = collect(client, run)
    submissions = [
        request
        for request in transport.requests
        if request.method == "POST" and request.url.path == "/v2/bulk-jobs"
    ]
    assert len(submissions) == 1
    assert json.loads(submissions[0].content)["options"]["storage"] == storage
    assert job_id == transport.job_id
    assert summary["completed"] == 2
    assert summary["failed"] == 1
    for path in run.rglob("*"):
        if path.is_file():
            contents = path.read_text(encoding="utf-8")
            for secret in [
                storage["access_key"],
                storage["secret_key"],
                storage["session_token"],
                "fixture-api-key",
            ]:
                assert secret not in contents
