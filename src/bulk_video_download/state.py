"""Small, atomic, credential-free run receipts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

from .inputs import file_hash


def write_json(path: Path, value: dict) -> None:
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_run(run_dir: str | Path) -> dict:
    path = Path(run_dir)
    state = json.loads((path / "run.json").read_text(encoding="utf-8"))
    if not isinstance(state, dict) or (state.get("version"), state.get("source")) != (
        1,
        "youtube_download",
    ):
        raise ValueError("Not a compatible bulk video download run.")
    if not re.fullmatch(r"bulk_[A-Za-z0-9_-]+", str(state.get("job_id", ""))):
        raise ValueError(
            "No accepted job ID was saved. Reconcile the submission in your console; "
            "do not automatically create another job. See docs/recovery.md."
        )
    if file_hash(path / "video-ids.txt") != state["input"]["sha256"]:
        raise ValueError("The saved ID file changed. Restore it before collecting this run.")
    return state
