import json

import httpx
import pytest
from flashdata import FlashData
from flashdata.errors import (
    APIError,
    ConnectionError,
    JobFailedError,
    JobPausedError,
    SubmissionUnknownError,
)

from bulk_video_download import collect, resume, start
from bulk_video_download.demo import DEMO_IDS, DemoTransport

STORAGE = {
    "storage_type": "s3",
    "storage_url": "test-bucket",
    "region": "us-east-1",
    "access_key": "test-access-key",
    "secret_key": "test-storage-secret",
}


@pytest.fixture
def setup(tmp_path):
    ids = tmp_path / "ids.txt"
    ids.write_text("\n".join(DEMO_IDS), encoding="utf-8")
    return ids, tmp_path / "run", DemoTransport()


def client_for(transport):
    return FlashData(api_key="test-api-key", transport=httpx.MockTransport(transport))


def mutations(transport):
    return [r for r in transport.requests if r.method in {"POST", "PUT", "PATCH", "DELETE"}]


def test_complete_workflow_and_reread_without_duplicate_submission(setup):
    ids, run, mock = setup
    with client_for(mock.handle) as client:
        job_id = start(client, ids, run_dir=run, storage=STORAGE)
        summary = collect(client, run)
        assert summary["completed"] == 2
        assert summary["failed"] == 1
        assert summary["media_bytes"] == 2000000
        assert (run / "results/failed-ids.txt").read_text().strip() == DEMO_IDS[2]
        assert (run / "results/completed-ids.txt").read_text().splitlines() == DEMO_IDS[:2]
        assert len((run / "results/deliveries.csv").read_text().splitlines()) == 3
        assert collect(client, run) == summary
        with pytest.raises(FileExistsError):
            start(client, ids, run_dir=run, storage=STORAGE)
    assert len(mutations(mock)) == 3  # create, upload, start
    state = (run / "run.json").read_text()
    assert job_id in state
    for secret in ("test-api-key", "test-storage-secret", "test-access-key", "https://storage"):
        assert secret not in state


def test_invalid_input_never_contacts_api(setup):
    ids, run, mock = setup
    ids.write_text("https://youtu.be/jNQXAC9IVRw", encoding="utf-8")
    with client_for(mock.handle) as client, pytest.raises(ValueError):
        start(client, ids, run_dir=run, storage=STORAGE)
    assert not mock.requests
    assert not run.exists()


@pytest.mark.parametrize("preset", ["mp3", "dataset"])
def test_presets_pass_the_real_sdk_request_validation(setup, preset):
    ids, run, mock = setup
    with client_for(mock.handle) as client:
        start(client, ids, run_dir=run, storage=STORAGE, preset=preset)
    options = json.loads(mutations(mock)[0].content)["options"]
    if preset == "mp3":
        assert options["download_type"] == "audio"
        assert options["output_format"] == "mp3"
        assert "video_quality" not in options
    else:
        assert options["download_type"] == "audio_video"
        assert options["video_quality"] == "best"
        assert options["upload_metadata"] is True


def test_lost_create_response_cannot_silently_create_again(setup):
    ids, run, mock = setup

    def lost(request):
        mock.handle(request)  # server may already have accepted it
        raise httpx.ReadTimeout("lost", request=request)

    with client_for(lost) as client:
        with pytest.raises(SubmissionUnknownError):
            start(client, ids, run_dir=run, storage=STORAGE)
        with pytest.raises(FileExistsError):
            start(client, ids, run_dir=run, storage=STORAGE)
        with pytest.raises(ValueError, match="No accepted job ID"):
            collect(client, run)
    assert len(mock.requests) == 1
    assert json.loads((run / "run.json").read_text())["phase"] == "submitting"


def test_lost_start_response_recovers_existing_job(setup):
    ids, run, mock = setup

    def lost(request):
        response = mock.handle(request)
        if request.url.path.endswith("/start"):
            raise httpx.ReadTimeout("lost", request=request)
        return response

    with client_for(lost) as client:
        with pytest.raises(SubmissionUnknownError):
            start(client, ids, run_dir=run, storage=STORAGE)
        assert resume(client, run)["completed"] == 2
    assert len(mutations(mock)) == 3


def test_failed_upload_keeps_job_id_and_does_not_create_replacement(setup):
    ids, run, mock = setup

    def failed(request):
        if request.method == "PUT":
            raise httpx.ConnectError("lost", request=request)
        if request.url.path.endswith("/start"):
            return httpx.Response(
                409, json={"code": "bulk_input_not_found", "message": "No upload"}
            )
        return mock.handle(request)

    with client_for(failed) as client:
        with pytest.raises(ConnectionError):
            start(client, ids, run_dir=run, storage=STORAGE)
        assert json.loads((run / "run.json").read_text())["job_id"] == mock.job_id
        with pytest.raises(APIError):
            resume(client, run)
    assert len([r for r in mock.requests if r.method == "POST"]) == 1


@pytest.mark.parametrize("status", ["paused", "failed", "cancelled"])
def test_terminal_and_paused_jobs_do_not_resubmit_or_publish(setup, status):
    ids, run, mock = setup

    def terminal(request):
        if request.url.path == f"/v2/bulk-jobs/{mock.job_id}" and request.method == "GET":
            return httpx.Response(200, json={"job": {**mock.job, "status": status}})
        return mock.handle(request)

    with client_for(terminal) as client:
        start(client, ids, run_dir=run, storage=STORAGE)
        with pytest.raises(JobPausedError if status == "paused" else JobFailedError):
            collect(client, run)
    assert len(mutations(mock)) == 3
    assert not (run / "results").exists()


def test_local_id_file_change_stops_recovery_before_network(setup):
    ids, run, mock = setup
    with client_for(mock.handle) as client:
        start(client, ids, run_dir=run, storage=STORAGE)
        count = len(mock.requests)
        (run / "video-ids.txt").write_text("aaaaaaaaaaa\n", encoding="utf-8")
        with pytest.raises(ValueError, match="changed"):
            collect(client, run)
    assert len(mock.requests) == count


@pytest.mark.parametrize(
    "corruption", ["missing", "duplicate", "wrong_id", "unknown_status", "wrong_source"]
)
def test_incomplete_or_mismatched_export_does_not_publish_retry_list(setup, corruption):
    ids, run, mock = setup
    original = json.loads(json.dumps(mock.rows))
    if corruption == "missing":
        mock.rows.pop()
    elif corruption == "duplicate":
        mock.rows.append(mock.rows[0])
    elif corruption == "wrong_id":
        mock.rows[0]["video_id"] = "aaaaaaaaaaa"
    elif corruption == "unknown_status":
        mock.rows[0]["status"] = "running"
    else:
        mock.rows[0]["source"] = "youtube_metadata"
    with client_for(mock.handle) as client:
        start(client, ids, run_dir=run, storage=STORAGE)
        with pytest.raises(ValueError):
            collect(client, run)
        assert not (run / "results").exists()
        mock.rows = original
        assert collect(client, run)["rows"] == 3
    assert len(mutations(mock)) == 3


def test_result_compaction_failure_is_not_a_media_retry(setup):
    ids, run, mock = setup
    mock.rows[-1]["error"]["code"] = "result_expired_before_compaction"
    with client_for(mock.handle) as client:
        start(client, ids, run_dir=run, storage=STORAGE)
        summary = collect(client, run)
    assert summary["needs_review"] == 1
    assert summary["failed"] == 0
    assert (run / "results/failed-ids.txt").read_bytes() == b""
    assert "result_expired_before_compaction" in (run / "results/failures.jsonl").read_text()


def test_network_interruption_during_export_can_collect_same_job_again(setup):
    ids, run, mock = setup
    broken = True

    def flaky(request):
        if broken and request.url.path == "/part":
            raise httpx.ReadError("broken result stream", request=request)
        return mock.handle(request)

    with client_for(flaky) as client:
        start(client, ids, run_dir=run, storage=STORAGE)
        with pytest.raises(ConnectionError):
            collect(client, run)
        assert not (run / "results").exists()
        broken = False
        assert collect(client, run)["completed"] == 2
    assert len(mutations(mock)) == 3
