# Recover a bulk download without submitting it twice

The run directory identifies one remote collection. Keep it when SSH disconnects,
Python exits, or polling times out. Recover with the same account/API key.

```bash
flashdata-bulk status --run runs/collection-01
flashdata-bulk collect --run runs/collection-01
```

`collect` only reads the saved job and its results. It never creates, uploads, starts,
resumes or cancels remote work. Completed local exports can be read even after the
remote result retention period has elapsed.

## Decide from the remote status

| Remote state | Action |
| --- | --- |
| `running` or `finalizing` | `collect` to continue waiting and export |
| `completed` | `collect` to download the result inventory |
| `paused` | Read `pauseReason`, resolve the cause, then explicitly `resume` |
| `awaiting_upload` | Use the draft recovery steps below |
| `failed` or `cancelled` | Inspect the job error; neither collect nor resume creates a replacement |

To change the local waiting period:

```bash
flashdata-bulk collect --run runs/collection-01 --timeout 7200 --poll-interval 10
```

This controls polling, not remote concurrency or the lifetime of the media downloads.

## The start response was lost

The accepted bulk ID was saved before uploading and starting. `status` reads the
server's current state. If it is running or completed, simply collect it.

```bash
flashdata-bulk resume --run runs/collection-01
```

`resume` reads the server first. It starts an `awaiting_upload` draft, explicitly resumes
a paused job, or collects an already-running/completed job. It never creates a new one.

## Upload was interrupted

The saved ID still identifies the draft. A `resume` attempts to start that draft;
the server checks whether its input was uploaded. A missing input returns an error.

The signed upload descriptor is used in memory and is **not saved** in `run.json`.
If the upload did not complete and that descriptor is gone, inspect the unused draft
in your console, or with `client.bulk.get(bulk_id)`. Cancel the unused draft explicitly
before intentionally starting a replacement in a new run directory. Do not repeatedly
create drafts in a retry loop.

```python
from flashdata import FlashData

with FlashData(api_key="your-flashdata-api-key") as client:
    print(client.bulk.get("bulk_your_saved_id"))
    # Only after confirming this is the unused draft you intend to cancel:
    # client.bulk.cancel("bulk_your_saved_id")
```

## Creation timed out before an ID was saved

`run.json` remains in phase `submitting`. Acceptance is unknown; automatically repeating
creation could create another collection. The tool stops rather than resubmitting.

Inspect recent jobs in your console or SDK:

```python
with FlashData(api_key="your-flashdata-api-key") as client:
    for job in client.bulk.iter_jobs(max_pages=3, limit=20):
        print(job["id"], job["source"], job["status"], job.get("createdAt"))
```

Match the request by account, source and time; do not assume the most recent job is yours
if multiple processes submit concurrently. Once the accepted ID is confirmed, add
`"job_id": "bulk_confirmed_id"` to the existing receipt, preserving the input hash,
then inspect/resume that job. If the state remains ambiguous, contact support with the
time and request ID before submitting again.

## Result collection was interrupted

Run `collect` again. It reads the same remote result parts. Until the entire inventory
matches the submitted IDs, nothing is published as a finished `results/` directory.
A completed export is preserved on subsequent calls.

Export result JSON promptly: FlashData result records have a 24-hour retention window
after completion. Your delivered media follows your bucket's retention settings.

## What the local guard covers

The existing run directory prevents this tool from submitting that run again. It is
not a server-side idempotency key. Another directory or machine can submit the same
IDs. Use one run directory per intentional collection and keep it with your job records.
