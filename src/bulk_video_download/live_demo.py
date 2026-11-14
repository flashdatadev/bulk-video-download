"""Opt-in real Bulk API demo: three ten-second MP4 clips delivered to your bucket."""

from pathlib import Path
from tempfile import TemporaryDirectory

from flashdata import FlashData

from .state import load_run
from .workflow import collect, start

DEMO_IDS = ("jNQXAC9IVRw", "aqz-KE-bpKQ", "M7lc1UVf-VE")
DEMO_OPTIONS = {
    "video_quality": "<=360",
    "start_at": "00:00:00",
    "end_at": "00:00:10",
}


def run_live_demo(client: FlashData, storage: dict, run_dir: Path, **collect_options) -> dict:
    """Submit once. Re-running collects the saved job, without starting new downloads."""
    if run_dir.exists():
        load_run(run_dir)
        ids = tuple((run_dir / "video-ids.txt").read_text(encoding="utf-8").splitlines())
        if ids != DEMO_IDS:
            raise ValueError("This run is not the three-video demo. Use collect for other runs.")
    else:
        with TemporaryDirectory(prefix="flashdata-live-demo-") as temporary:
            source = Path(temporary) / "ids.txt"
            source.write_text("\n".join(DEMO_IDS) + "\n", encoding="utf-8")
            start(client, source, run_dir=run_dir, storage=storage, **DEMO_OPTIONS)
    return collect(client, run_dir, **collect_options)
