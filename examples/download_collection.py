"""Edit the placeholder values, then run from the repository root."""

from pathlib import Path

from flashdata import FlashData

from bulk_video_download import collect, progress_line, start

storage = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
    "object_prefix": "collections/run-01",
}
run = Path("runs/collection-01")

with FlashData(api_key="your-flashdata-api-key") as client:
    if not run.exists():
        start(client, "sample-data/video-ids.txt", run_dir=run, storage=storage, preset="mp4")
    summary = collect(
        client,
        run,
        on_progress=lambda job, total: print(progress_line(job, total), flush=True),
    )
print(summary)
