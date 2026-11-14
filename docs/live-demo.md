# Run a real batch download

The `live-demo` command submits **one real FlashData Bulk API job** for these three videos. It requests the first ten seconds of each as an MP4 with video and audio, with a 360p ceiling. The media is delivered to your bucket; inventories are saved locally.

| Video | Video ID | Requested clip |
| --- | --- | --- |
| Me at the zoo | `jNQXAC9IVRw` | 00:00:00–00:00:10 |
| Big Buck Bunny | `aqz-KE-bpKQ` | 00:00:00–00:00:10 |
| YouTube Developers video | `M7lc1UVf-VE` | 00:00:00–00:00:10 |

## Run it

Install using the [README quickstart](../README.md#quickstart-bulk-download-youtube-videos), then:

```bash
flashdata-bulk init
```

Edit `config.py`: put your API key directly in `API_KEY` and fill in `STORAGE`. [Storage settings](storage.md) include S3 and Cloudflare R2. Use a dedicated prefix such as `demos/bulk-video-download`. Keep the configuration private.

```bash
flashdata-bulk live-demo
```

This command uses API credits. It prints progress from the live job and the actual completed/failed counts and delivered bytes after export. It does not supply canned success results. `OPTIONS` in your config applies to regular `run` commands; this demo always uses the small clip settings above.

Prefer Python? Copy [live_batch_demo.py](../examples/live_batch_demo.py) into a private file, supply your key in `FlashData(api_key="your-flashdata-api-key")`, and run it.

## Inspect the delivery

Open `runs/live-demo/results/deliveries.csv`, then find those objects in your bucket. Play the clips to verify video and audio. The summary is in `summary.json`; full per-video outcomes are in `results.jsonl`. These files describe the **actual run**, including any failures.

The demo never downloads media into the local results folder. For a private bucket, use your storage console or storage SDK to view the delivered MP4s. Object URLs do not automatically grant public access.

## Continue the same run

```bash
flashdata-bulk live-demo
```

Re-running reads the saved job; it does not create a replacement. If the process stopped during upload/start, or the service paused the job, follow [recovery](recovery.md). Use `--run runs/live-demo-02` only when you intentionally want another collection.

## Share evidence from your run

Publish the date, clip settings, counts, delivered byte sizes, and a screenshot of the three delivered clips. Keep API keys, storage credentials, signed URLs, private bucket names and raw receipts out of public screenshots and commits. Generated run files are gitignored.

The separate `flashdata-bulk demo` command is an **offline simulation** used for testing. Its synthetic results are not evidence of live download performance.
