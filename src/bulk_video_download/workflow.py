"""Submit once, inspect progress, recover the same job and collect its inventory."""

from __future__ import annotations

import math
import re
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from flashdata import FlashData
from flashdata.errors import JobFailedError, JobPausedError, PollingTimeoutError, ProtocolError

from .exports import export_rows
from .inputs import prepare_ids
from .state import load_run, write_json

PRESETS = {
    "mp4": {"download_type": "audio_video", "output_format": "mp4", "video_quality": "<=1080"},
    "mp3": {"download_type": "audio", "output_format": "mp3", "audio_quality": "192"},
    "dataset": {
        "download_type": "audio_video",
        "output_format": "mp4",
        "video_quality": "best",
        "upload_metadata": True,
    },
}


def start(
    client: FlashData,
    input_file: str | Path,
    *,
    run_dir: str | Path,
    storage: dict,
    preset: str = "mp4",
    **options,
) -> str:
    """Create one collection. Existing run directories are never submitted again."""
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    if "storage" in options or "source" in options:
        raise ValueError("Pass storage separately; source is always youtube_download.")
    directory = Path(run_dir)
    if directory.exists():
        raise FileExistsError(f"Run already exists: {directory}. Use collect or resume.")
    directory.parent.mkdir(parents=True, exist_ok=True)
    # Fully validate locally before reserving the run or sending a network request.
    with TemporaryDirectory(prefix=".input-", dir=directory.parent) as temporary:
        normalized = Path(temporary) / "video-ids.txt"
        stats = prepare_ids(input_file, normalized)
        directory.mkdir()
        shutil.copyfile(normalized, directory / "video-ids.txt")
    state = {"version": 1, "source": "youtube_download", "phase": "submitting", "input": stats}
    receipt_path = directory / "run.json"
    write_json(receipt_path, state)
    created = client.bulk.create(
        {
            "source": "youtube_download",
            "options": {**PRESETS[preset], **options, "storage": storage},
        }
    )
    job_id = created.get("job", {}).get("id")
    if not isinstance(job_id, str) or not re.fullmatch(r"bulk_[A-Za-z0-9_-]+", job_id):
        raise ProtocolError("Creation returned no valid job ID. Reconcile before retrying.")
    state.update(job_id=job_id, phase="created")
    try:
        write_json(receipt_path, state)
    except OSError:
        raise OSError(f"Job accepted: {job_id}. Save this ID; the local write failed.") from None
    client.bulk.upload_file(created, directory / "video-ids.txt")
    state["phase"] = "uploaded"
    write_json(receipt_path, state)
    client.bulk.start(job_id)
    state["phase"] = "started"
    write_json(receipt_path, state)
    return job_id


def _get(client: FlashData, state: dict, *, timeout: float | None = None) -> dict:
    job = client.bulk.get(state["job_id"], timeout=timeout)
    if job.get("id") != state["job_id"] or job.get("source") != "youtube_download":
        raise ProtocolError("The server returned a different job or source.")
    return job


def status(client: FlashData, run_dir: str | Path) -> dict:
    """Read a saved job. No submission, upload, start or resume request."""
    return _get(client, load_run(run_dir))


def progress_line(job: dict, total: int) -> str:
    counts = job.get("counts", {})
    done, failed = counts.get("completed", 0), counts.get("failed", 0)
    return (
        f"{job['id']} | {job['status']} | {done + failed}/{total} finished"
        f" | {done} delivered | {failed} failed"
    )


def collect(
    client: FlashData,
    run_dir: str | Path,
    *,
    timeout: float = 3600,
    poll_interval: float = 5,
    on_progress: Callable[[dict, int], None] | None = None,
) -> dict:
    """Wait for an existing job and publish a complete inventory. Never submit work."""
    if not all(math.isfinite(v) and v > 0 for v in (timeout, poll_interval)):
        raise ValueError("Timeout and poll interval must be positive and finite.")
    directory = Path(run_dir)
    state = load_run(directory)
    if (directory / "results").exists():
        return export_rows(directory, state, (), {})
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise PollingTimeoutError(state["job_id"])
        job = _get(client, state, timeout=min(remaining, client.timeout))
        if on_progress:
            on_progress(job, state["input"]["unique"])
        current = job.get("status")
        if current == "completed":
            break
        if current == "paused":
            raise JobPausedError(job)
        if current in {"failed", "cancelled"}:
            raise JobFailedError(job)
        if current == "awaiting_upload":
            raise ValueError("This draft has not started. See docs/recovery.md or use resume.")
        if current not in {"running", "finalizing"}:
            raise ProtocolError("Unexpected bulk job status.")
        time.sleep(min(poll_interval, max(0, deadline - time.monotonic())))
    manifest = client.bulk.manifest(state["job_id"])
    summary = export_rows(directory, state, client.bulk.rows(state["job_id"]), manifest)
    state["phase"] = "completed"
    write_json(directory / "run.json", state)
    return summary


def resume(client: FlashData, run_dir: str | Path, **collect_options) -> dict:
    """Explicitly continue the saved draft/paused job, then collect that same ID."""
    state = load_run(run_dir)
    job = _get(client, state)
    if job["status"] == "awaiting_upload":
        # Server checks the uploaded input. No upload descriptor is stored on disk.
        client.bulk.start(state["job_id"])
    elif job["status"] == "paused":
        client.bulk.resume(state["job_id"])
    return collect(client, run_dir, **collect_options)
