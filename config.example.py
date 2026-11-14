"""Copy to config.py. The private copy is gitignored; use placeholders only here."""

API_KEY = "your-flashdata-api-key"
STORAGE = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
    "object_prefix": "collections/run-01",
}
# Optional overrides applied to the selected preset, e.g. {"video_quality": "<=720"}.
OPTIONS = {}
