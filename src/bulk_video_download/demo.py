"""An explicitly synthetic, no-network demo exercising the real SDK and export path."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from flashdata import FlashData

from .workflow import collect, progress_line, start

DEMO_IDS = ["jNQXAC9IVRw", "dQw4w9WgXcQ", "9bZkp7q19f0"]


class DemoTransport:
    """Synthetic media locations do not exist. Every HTTP request stays in memory."""

    def __init__(self):
        self.requests = []
        self.started = False
        self.job_id = "bulk_offline_demo"
        self.rows = [
            {
                "index": i,
                "job_id": f"job_offline_{i}",
                "source": "youtube_download",
                "video_id": video_id,
                "status": "completed",
                "results": [{"file_url": f"s3://demo-bucket/{video_id}.mp4", "file_size": 1000000}],
            }
            for i, video_id in enumerate(DEMO_IDS[:2])
        ] + [
            {
                "index": 2,
                "job_id": "job_offline_2",
                "source": "youtube_download",
                "video_id": DEMO_IDS[2],
                "status": "failed",
                "error": {
                    "code": "demo_failure",
                    "detail": "Synthetic failure for the retry example",
                },
            }
        ]

    @property
    def job(self):
        return {
            "id": self.job_id,
            "source": "youtube_download",
            "status": "completed" if self.started else "awaiting_upload",
            "counts": {"accepted": 3, "completed": 2, "failed": 1, "invalid": 0},
        }

    @property
    def manifest(self):
        return {**self.job, "status": "completed", "parts": [{"number": 1}]}

    def handle(self, request):
        self.requests.append(request)
        path = request.url.path
        if request.url.host == "storage.example.com":
            assert "x-api-key" not in request.headers
            if path == "/input" and request.method == "PUT":
                assert request.content == ("\n".join(DEMO_IDS) + "\n").encode()
                return httpx.Response(200)
            if path == "/manifest":
                return httpx.Response(200, json=self.manifest)
            if path == "/part":
                content = "\n".join(json.dumps(row) for row in self.rows).encode()
                return httpx.Response(200, content=gzip.compress(content))
        if request.url.host == "api.flashdata.dev":
            if path == "/v2/api-access":
                return httpx.Response(200, json={"result_origin": "https://storage.example.com"})
            if path == "/v2/bulk-jobs" and request.method == "POST":
                return httpx.Response(
                    201,
                    json={
                        "job": self.job,
                        "upload": {
                            "href": "https://storage.example.com/input",
                            "method": "PUT",
                            "contentType": "text/plain; charset=utf-8",
                        },
                    },
                )
            if path == f"/v2/bulk-jobs/{self.job_id}/start":
                self.started = True
                return httpx.Response(200, json={"job": self.job})
            if path == f"/v2/bulk-jobs/{self.job_id}":
                return httpx.Response(200, json={"job": self.job})
            if path.endswith("/results"):
                return httpx.Response(
                    302, headers={"Location": "https://storage.example.com/manifest"}
                )
            if path.endswith("/results/1"):
                return httpx.Response(302, headers={"Location": "https://storage.example.com/part"})
        raise AssertionError(f"Unexpected offline request: {request.method} {path}")


def run_demo(run_dir: str | Path) -> dict:
    transport = DemoTransport()
    with FlashData(
        api_key="offline-demo-key", transport=httpx.MockTransport(transport.handle)
    ) as client:
        if not Path(run_dir).exists():
            with TemporaryDirectory() as temporary:
                ids = Path(temporary) / "ids.txt"
                ids.write_text("\n".join(DEMO_IDS), encoding="utf-8")
                start(
                    client,
                    ids,
                    run_dir=run_dir,
                    storage={
                        "storage_type": "s3",
                        "storage_url": "demo-bucket",
                        "region": "us-east-1",
                        "access_key": "demo-key",
                        "secret_key": "demo-secret",
                    },
                )
        return collect(
            client,
            run_dir,
            on_progress=lambda job, total: print(progress_line(job, total), flush=True),
        )
