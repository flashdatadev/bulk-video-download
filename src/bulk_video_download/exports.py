"""Publish complete, reconciled inventories; never turn missing results into retries."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from tempfile import TemporaryDirectory

from .state import write_json

# These describe lost result records, not a confirmed failed media download.
RESULT_ERRORS = {"invalid_child_result", "result_expired_before_compaction"}


def csv_value(value: object) -> str:
    text = str(value if value is not None else "")
    return "'" + text if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")) else text


def export_rows(run_dir: Path, state: dict, rows: Iterable[dict], manifest: dict) -> dict:
    """Reconcile indexes/IDs using SQLite, then atomically publish the results directory."""
    destination = run_dir / "results"
    if destination.exists():
        summary = json.loads((destination / "summary.json").read_text(encoding="utf-8"))
        if (summary.get("job_id"), summary.get("input_sha256")) != (
            state["job_id"],
            state["input"]["sha256"],
        ):
            raise ValueError("Existing results do not belong to this run.")
        return summary
    if manifest.get("id") != state["job_id"] or manifest.get("status") != "completed":
        raise ValueError("Result manifest does not describe this completed job.")
    summary = {
        "job_id": state["job_id"],
        "input_sha256": state["input"]["sha256"],
        "input_videos": state["input"]["unique"],
        "rows": 0,
        "completed": 0,
        "failed": 0,
        "needs_review": 0,
        "media_files": 0,
        "media_bytes": 0,
    }
    with TemporaryDirectory(prefix=".export-", dir=run_dir) as temporary:
        staging = Path(temporary)
        published = staging / "results"
        published.mkdir()
        db = sqlite3.connect(staging / "inventory.sqlite")
        try:
            db.execute("CREATE TABLE inputs (idx INTEGER PRIMARY KEY, video_id TEXT, seen INTEGER)")
            with (run_dir / "video-ids.txt").open(encoding="utf-8") as source:
                db.executemany(
                    "INSERT INTO inputs VALUES (?, ?, 0)",
                    ((index, line.strip()) for index, line in enumerate(source)),
                )
            with (
                (published / "results.jsonl").open("w", encoding="utf-8") as all_rows,
                (published / "failures.jsonl").open("w", encoding="utf-8") as failures,
                (published / "failed-ids.txt").open("w", encoding="utf-8", newline="\n") as failed,
                (published / "completed-ids.txt").open("w", encoding="utf-8", newline="\n") as done,
                (published / "deliveries.csv").open("w", encoding="utf-8", newline="") as csv_file,
            ):
                writer = csv.writer(csv_file)
                writer.writerow(["video_id", "job_id", "file_url", "file_size"])
                for row in rows:
                    if not isinstance(row, dict) or type(row.get("index")) is not int:
                        raise ValueError("A result row has no valid input index.")
                    matched = db.execute(
                        "UPDATE inputs SET seen=1 WHERE idx=? AND video_id=? AND seen=0",
                        (row["index"], row.get("video_id")),
                    )
                    if matched.rowcount != 1:
                        raise ValueError(
                            "Duplicate result index or result does not match the input."
                        )
                    status = row.get("status")
                    if row.get("source") != "youtube_download" or status not in {
                        "completed",
                        "failed",
                    }:
                        raise ValueError("Unexpected result source or nonterminal result status.")
                    encoded = json.dumps(row, ensure_ascii=False) + "\n"
                    all_rows.write(encoded)
                    summary["rows"] += 1
                    if status == "completed":
                        media = row.get("results")
                        if not isinstance(media, list) or not media:
                            raise ValueError("Completed item has no delivery records.")
                        for item in media:
                            if not isinstance(item, dict) or not isinstance(
                                item.get("file_url"), str
                            ):
                                raise ValueError("Completed item has no media location.")
                            size = item.get("file_size")
                            if type(size) is not int or size < 0 or not item["file_url"].strip():
                                raise ValueError("Invalid delivered file size or location.")
                            writer.writerow(
                                [
                                    csv_value(v)
                                    for v in (
                                        row["video_id"],
                                        row.get("job_id"),
                                        item["file_url"],
                                        size,
                                    )
                                ]
                            )
                            summary["media_files"] += 1
                            summary["media_bytes"] += size
                        done.write(row["video_id"] + "\n")
                        summary["completed"] += 1
                    else:
                        failures.write(encoded)
                        code = (row.get("error") or {}).get("code")
                        if not code or code in RESULT_ERRORS:
                            summary["needs_review"] += 1
                        else:
                            failed.write(row["video_id"] + "\n")
                            summary["failed"] += 1
                    if summary["rows"] % 10000 == 0:
                        db.commit()
            missing = db.execute("SELECT COUNT(*) FROM inputs WHERE seen=0").fetchone()[0]
            if missing or summary["rows"] != summary["input_videos"]:
                raise ValueError(f"Incomplete export: {missing} input videos have no result row.")
            write_json(published / "summary.json", summary)
            write_json(published / "manifest.json", manifest)
            # Every file is closed and complete before it becomes an authoritative retry list.
            os.rename(published, destination)
        finally:
            db.close()
    return summary
