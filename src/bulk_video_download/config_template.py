"""Placeholder-only configuration, included in the wheel for clone-free setup."""

from pathlib import Path

TEMPLATE = '''"""Private local configuration. Do not commit credentials."""

API_KEY = "your-flashdata-api-key"
STORAGE = {
    "storage_type": "s3",
    "storage_url": "your-media-bucket",
    "region": "us-east-1",
    "access_key": "your-storage-access-key",
    "secret_key": "your-storage-secret-key",
    # With temporary keys, include the token from that same session:
    # "session_token": "your-session-token",
    "object_prefix": "collections/run-01",
}
# Optional overrides for `run`; the live demo always uses its fixed small clip settings.
OPTIONS = {}
'''


def create_config(path: Path) -> None:
    """Create a private placeholder file, without replacing an existing configuration."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        output.write(TEMPLATE)
