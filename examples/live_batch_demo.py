"""Three real ten-second MP4 downloads through one saved Bulk API job."""

from pathlib import Path

from flashdata import FlashData

from bulk_video_download import progress_line
from bulk_video_download.live_demo import run_live_demo

if __name__ == "__main__":
    storage = {
        "storage_type": "s3",
        "storage_url": "your-media-bucket",
        "region": "us-east-1",
        "access_key": "your-storage-access-key",
        "secret_key": "your-storage-secret-key",
        "object_prefix": "demos/bulk-video-download",
    }
    with FlashData(api_key="your-flashdata-api-key") as client:
        summary = run_live_demo(
            client,
            storage,
            Path("runs/live-demo"),
            on_progress=lambda job, total: print(progress_line(job, total), flush=True),
        )
    print(summary)
    print("Open runs/live-demo/results/deliveries.csv for the delivered object locations.")
