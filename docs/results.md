# Delivery inventory and selective retries

`results.jsonl` preserves each returned record. An illustrative completed row is:

```json
{"index":0,"job_id":"job_example","source":"youtube_download","video_id":"jNQXAC9IVRw","status":"completed","results":[{"file_url":"s3://example-bucket/collection/video.mp4","file_size":635505}]}
```

This is a schema example, not a live delivery. Actual URLs and metadata come from the
API. `index` is the zero-based position in the normalized `video-ids.txt`. Completion
order can differ from input order; use `video_id` or `index` when joining records.

## Read the outputs

| File | Use |
| --- | --- |
| `results.jsonl` | Full API results, usage and errors |
| `deliveries.csv` | One row per returned media file: ID, job ID, URL and byte size |
| `completed-ids.txt` | IDs whose media delivery completed |
| `failures.jsonl` | Failed rows with error codes and details |
| `failed-ids.txt` | Only confirmed download failures |
| `summary.json` | Local inventory totals, input hash and job ID |
| `manifest.json` | Result part manifest, counts and expiry when returned |

`media_bytes` sums the reported `file_size` values. It is an inventory measurement,
not an account billing statement. Full returned metadata remains in JSONL. CSV cells
beginning with spreadsheet formula characters are prefixed with an apostrophe; use
JSONL when you need the exact original field values.

## Retry a failed subset

1. Read `failures.jsonl` and resolve problems such as storage write permissions.
2. Keep the original run and its delivered objects.
3. Submit `failed-ids.txt` in a **new** run directory, with suitable output settings.

```bash
flashdata-bulk run runs/collection-01/results/failed-ids.txt --run runs/retry-01
```

The retry is an explicit new API job and uses credits. The tool does not retry the
entire original file, and rejects an empty retry file before any API call.

## Missing records are not failed downloads

A lost result does not establish whether a media object was delivered. These rows are
kept for inspection and counted in `needs_review`, without adding the ID to a retry:

- `result_expired_before_compaction`
- `invalid_child_result`
- Failure rows without an error code

Check the bucket and job details before downloading those items again.

Duplicate indexes, mismatched video IDs, unknown statuses or missing rows abort the
export. Collect again after resolving the result issue; no partial retry list is
published. The disk-backed reconciliation index avoids keeping every result in RAM.
