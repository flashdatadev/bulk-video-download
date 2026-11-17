# Cloud storage for bulk video downloads

Create a bucket and credentials that can write the destination prefix. Supply these
settings directly in your Python code, or in the CLI's private `config.py`.

## Amazon S3

```python
STORAGE = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
    "object_prefix": "collections/run-01",
}
```

Use the bucket's actual region. `storage_url` is the bucket name in this configuration,
not an HTTPS video URL. The prefix groups this collection's delivered objects.

## Cloudflare R2 / S3-compatible storage

```python
STORAGE = {
    "storage_type": "s3_compatible",
    "storage_url": "your-r2-bucket",
    "region": "auto",
    "endpoint_url": "https://your-account-id.r2.cloudflarestorage.com",
    "access_key": "your-r2-access-key",
    "secret_key": "your-r2-secret-key",
    "object_prefix": "collections/run-01",
}
```

Use the account's S3 API endpoint, not a public R2 custom domain. The SDK/API also
support other storage providers; see the authoritative [storage parameters](https://flashdata.dev/docs/sources/youtube_download#storage)
for GCS, Azure, OSS, COS, BOS and TOS.

## Temporary credentials (STS)

SDK 1.3 or later accepts `session_token` in the storage configuration, together
with the matching temporary `access_key` and `secret_key`. For example:

```python
from flashdata import FlashData
from bulk_video_download import start

storage = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "object_prefix": "collections/sts-run-01",
    "access_key": "your-temporary-access-key",
    "secret_key": "your-temporary-secret-key",
    "session_token": "your-session-token",
}

with FlashData(api_key="your-flashdata-api-key") as client:
    job_id = start(
        client,
        "video-ids.txt",
        run_dir="runs/sts-run-01",
        storage=storage,
        preset="mp4",
    )
    print(job_id)
```

The toolkit sends the complete credential set in `options.storage` when creating
the bulk job. The CLI accepts the same `STORAGE` dictionary in its private
`config.py`; no new flag is needed. Credentials are excluded from `run.json`.

| `storage_type` | Token supplied as `session_token` |
| --- | --- |
| `s3` | AWS STS `SessionToken` |
| `s3_compatible` | The provider's S3 session token, if supported |
| `oss` | Alibaba Cloud STS `SecurityToken` |
| `cos` | Tencent Cloud `Token`, with `TmpSecretId` / `TmpSecretKey` as the key pair |
| `bos` | Baidu Cloud STS session token |
| `tos` | Volcengine STS `SessionToken` |

Keep the provider's usual endpoint, region and bucket fields. Omit the token for
long-term access keys, GCS and Azure. Tokens must be nonempty strings of at most
16,384 characters without whitespace or control characters.

Choose credentials whose lifetime covers the entire collection: queueing,
downloads, uploads and retries. FlashData and this toolkit do not refresh them
automatically. If a credential expires, inspect the job and its per-video results.
Once failures are confirmed, replace the complete key pair and token in your
private configuration and submit only `results/failed-ids.txt` in a new run
directory. Keep the original completed exports. See [recovery](recovery.md).

## Read delivered media

Open `results/deliveries.csv` or inspect `results.jsonl`. A private object is read with
your storage credentials or a provider-generated signed URL. The recorded location
does not automatically grant anonymous access.

The [general download toolkit](https://github.com/flashdatadev/youtube-video-download-api)
has an S3/R2 retrieval example for copying an object to local disk. Keep that stage
separate from collection: a local file copy failure should not trigger another YouTube
download.

## Troubleshoot storage failures

Check bucket existence, provider/endpoint, region, credential validity, and permission
to write the selected prefix. Use a small collection first to verify object delivery.
After fixing storage, retry the confirmed failed IDs in a new run directory.

`run.json` contains no storage credentials or signed upload descriptor. Your private
Python configuration and local delivery inventories should remain outside commits.
