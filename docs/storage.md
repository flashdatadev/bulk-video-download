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
    "storage_type": "s3",
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
