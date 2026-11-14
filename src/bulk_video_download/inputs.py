"""Validate and deduplicate ID files without keeping the collection in RAM."""

from __future__ import annotations

import hashlib
import re
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory

VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}\Z")
MAX_INPUT_BYTES = 2 * 1024**3


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_ids(source: str | Path, destination: str | Path) -> dict:
    """Write unique IDs in first-seen order; reject bad lines before publishing output."""
    source, destination = Path(source), Path(destination)
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stats = {"lines": 0, "unique": 0, "duplicates": 0, "blank": 0}
    with TemporaryDirectory(prefix=".prepare-", dir=destination.parent) as temporary:
        clean = Path(temporary) / "ids.txt"
        with closing(sqlite3.connect(Path(temporary) / "seen.sqlite")) as db:
            db.execute("CREATE TABLE ids (video_id TEXT PRIMARY KEY)")
            with (
                source.open(encoding="utf-8-sig") as incoming,
                clean.open("w", encoding="utf-8", newline="\n") as outgoing,
            ):
                for line_number, line in enumerate(incoming, 1):
                    stats["lines"] += 1
                    video_id = line.strip()
                    if not video_id:
                        stats["blank"] += 1
                        continue
                    if not VIDEO_ID.fullmatch(video_id):
                        raise ValueError(
                            f"Line {line_number}: expected an 11-character YouTube video ID. "
                            "Use IDs only, not URLs, playlist links, headers or JSON."
                        )
                    inserted = db.execute("INSERT OR IGNORE INTO ids VALUES (?)", (video_id,))
                    if inserted.rowcount:
                        outgoing.write(video_id + "\n")
                        stats["unique"] += 1
                    else:
                        stats["duplicates"] += 1
                    if stats["unique"] * 12 > MAX_INPUT_BYTES:
                        raise ValueError("Prepared ID file exceeds the Bulk API's 2 GiB limit.")
                    if line_number % 10000 == 0:
                        db.commit()
        if not stats["unique"]:
            raise ValueError("Input contains no video IDs.")
        stats["sha256"] = file_hash(clean)
        # Exclusive create protects an existing destination, including concurrent writers.
        with destination.open("xb") as target, clean.open("rb") as staged:
            shutil.copyfileobj(staged, target)
    return stats
