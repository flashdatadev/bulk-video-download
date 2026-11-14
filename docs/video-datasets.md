# Build a video dataset from a bulk download

A reusable collection needs media, stable IDs and an inventory. Begin with a curated
ID file from your discovery process. Keep the selection criteria and collection date
alongside it so the dataset can be reproduced.

## 1. Download MP4 and companion metadata

The `dataset` preset requests best video plus audio, MP4 output and companion metadata:

```bash
flashdata-bulk run video-ids.txt --preset dataset --run runs/dataset-01
```

The equivalent Python call, after configuring a client and storage, is:

```python
start(client, "video-ids.txt", run_dir="runs/dataset-01", storage=storage, preset="dataset")
summary = collect(client, "runs/dataset-01")
```

If 1080p is enough for your model, cap resolution to reduce delivered volume:

```python
start(
    client,
    "video-ids.txt",
    run_dir="runs/dataset-1080p",
    storage=storage,
    preset="dataset",
    video_quality="<=1080",
)
```

For an advanced video/audio stream selection, the API accepts `yt_dlp_format`; see
the [download reference](https://flashdata.dev/docs/sources/youtube_download). Use a
separate run for each intentional output profile.

## 2. Join transcripts by video ID

`upload_metadata=True` delivers companion metadata; it does **not** request transcripts.
Feed `results/completed-ids.txt` into your transcript/caption collection stage and join
its output with media records by `video_id`.

[YouTube Transcript API Toolkit](https://github.com/flashdatadev/youtube-transcript-api)
provides transcript retrieval and subtitle export. Preserve that stage's success/failure
separately: missing captions should not cause you to download successful media again.

## 3. Hand off a collection manifest

Keep the normalized input, run receipt, result manifest, full JSONL, delivery CSV and
selection notes together. Store your own annotations or labels keyed by `video_id`.
Use `failed-ids.txt` for an intentional retry after inspecting failures.

Do not treat a completed bulk job as proof that every source delivered. Read the
summary's completed, failed and needs-review counts; the per-video inventory is the
handoff record.

## Managed sourcing and delivery

If you need help sourcing video IDs, agreeing collection requirements or arranging
delivery, see [FlashData YouTube Video Datasets](https://flashdata.dev/products/youtube-video-datasets?utm_source=github&utm_medium=docs&utm_campaign=bulk-video-download).
This repository covers self-service API collection from an ID file.
