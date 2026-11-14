"""Validate and deduplicate ID files without keeping the collection in RAM."""

from __future__ import annotations

import csv
import hashlib
import re
import shutil
import sqlite3
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit

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
    with Path(source).open(encoding="utf-8-sig") as incoming:
        return _prepare(enumerate(incoming, 1), Path(destination), urls=False)


def video_id_from_url(value: str) -> str:
    """Parse a video ID or supported YouTube URL locally, without resolving redirects."""
    value = value.strip()
    if VIDEO_ID.fullmatch(value):
        return value
    if any(character.isspace() for character in value) or "\\" in value:
        raise ValueError("Expected one YouTube video URL or 11-character ID.")
    parsed = urlsplit(value)
    hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port is not None
        or parsed.hostname not in hosts | {"youtu.be", "www.youtu.be", "www.youtube-nocookie.com"}
    ):
        raise ValueError("Use an http(s) YouTube video URL, not a redirect or another website.")
    parts = parsed.path.strip("/").split("/")
    video_id = ""
    if parsed.hostname in {"youtu.be", "www.youtu.be"} and len(parts) == 1:
        video_id = parts[0]
    elif parsed.hostname in hosts and parsed.path.rstrip("/") == "/watch":
        values = parse_qs(parsed.query, keep_blank_values=True).get("v", [])
        if len(values) == 1:
            video_id = values[0]
    elif len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
        if parsed.hostname in hosts or (
            parsed.hostname == "www.youtube-nocookie.com" and parts[0] == "embed"
        ):
            video_id = parts[1]
    if not VIDEO_ID.fullmatch(video_id):
        raise ValueError("Expected a single video URL; playlist/channel links are not expanded.")
    return video_id


def import_urls(source: str | Path, destination: str | Path, *, column: str | None = None) -> dict:
    """Import text lines or an explicitly named CSV column into the API's ID-only format."""
    with Path(source).open(encoding="utf-8-sig", newline="") as incoming:
        if column is None:
            return _prepare(enumerate(incoming, 1), Path(destination), urls=True)
        reader = csv.DictReader(incoming, strict=True)
        if not reader.fieldnames or reader.fieldnames.count(column) != 1:
            raise ValueError(f"CSV must have exactly one column named {column!r}.")

        def values():
            for row in reader:
                if None in row or row.get(column) is None:
                    raise ValueError(f"Line {reader.line_num}: malformed CSV row.")
                yield reader.line_num, row[column]

        try:
            return _prepare(values(), Path(destination), urls=True)
        except csv.Error as error:
            raise ValueError(f"Line {reader.line_num}: invalid CSV.") from error


def _prepare(values: Iterable[tuple[int, str]], destination: Path, *, urls: bool) -> dict:
    if destination.exists():
        raise FileExistsError(f"Output already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    stats = {"lines": 0, "unique": 0, "duplicates": 0, "blank": 0}
    with TemporaryDirectory(prefix=".prepare-", dir=destination.parent) as temporary:
        clean = Path(temporary) / "ids.txt"
        with closing(sqlite3.connect(Path(temporary) / "seen.sqlite")) as db:
            db.execute("CREATE TABLE ids (video_id TEXT PRIMARY KEY)")
            with clean.open("w", encoding="utf-8", newline="\n") as outgoing:
                for line_number, line in values:
                    stats["lines"] += 1
                    video_id = line.strip()
                    if not video_id:
                        stats["blank"] += 1
                        continue
                    if urls:
                        try:
                            video_id = video_id_from_url(video_id)
                        except ValueError as error:
                            raise ValueError(f"Line {line_number}: {error}") from error
                    elif not VIDEO_ID.fullmatch(video_id):
                        raise ValueError(
                            f"Line {line_number}: expected an 11-character YouTube video ID. "
                            "Use IDs only. Convert URL/CSV lists with the import command first."
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
