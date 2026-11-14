"""Small CLI; credentials live in a private Python config, never command arguments."""

from __future__ import annotations

import argparse
import json
import math
import runpy
import sys
from pathlib import Path

from flashdata import FlashData
from flashdata.errors import FlashDataError

from .inputs import prepare_ids
from .workflow import PRESETS, collect, progress_line, resume, start, status


def positive(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Must be positive and finite")
    return number


def report(job: dict, total: int) -> None:
    print(progress_line(job, total), flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Bulk video download from YouTube to cloud storage"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare", help="Validate/deduplicate IDs offline")
    prepare.add_argument("input", type=Path)
    prepare.add_argument("output", type=Path)
    demo = commands.add_parser("demo", help="Run a synthetic offline collection")
    demo.add_argument("--run", type=Path, default=Path("runs/demo"))
    for name in ("run", "collect", "status", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, default=Path("config.py"))
        command.add_argument("--run", type=Path, required=True)
        if name != "status":
            command.add_argument("--timeout", type=positive, default=3600)
            command.add_argument("--poll-interval", type=positive, default=5)
        if name == "run":
            command.add_argument("input", type=Path)
            command.add_argument("--preset", choices=PRESETS, default="mp4")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            print(json.dumps(prepare_ids(args.input, args.output), indent=2))
            return 0
        if args.command == "demo":
            from .demo import run_demo

            print("OFFLINE DEMO: synthetic responses; no media download or API requests.")
            print(json.dumps(run_demo(args.run), indent=2))
            return 0
        if not args.config.is_file():
            raise ValueError(
                "Copy config.example.py to config.py and fill in your Python settings."
            )
        settings = runpy.run_path(str(args.config))
        api_key = settings.get("API_KEY")
        if not isinstance(api_key, str) or not api_key.strip() or api_key.startswith("your-"):
            raise ValueError("Set API_KEY in your private Python config.")
        with FlashData(api_key=api_key) as client:
            if args.command == "status":
                print(json.dumps(status(client, args.run), indent=2))
                return 0
            if args.command == "run":
                storage = settings.get("STORAGE")
                if not isinstance(storage, dict) or not storage:
                    raise ValueError("Set STORAGE in your private Python config before submission.")
                job_id = start(
                    client,
                    args.input,
                    run_dir=args.run,
                    storage=storage,
                    preset=args.preset,
                    **settings.get("OPTIONS", {}),
                )
                print(f"Saved {job_id} in {args.run / 'run.json'}", flush=True)
            operation = resume if args.command == "resume" else collect
            summary = operation(
                client,
                args.run,
                timeout=args.timeout,
                poll_interval=args.poll_interval,
                on_progress=report,
            )
        print(json.dumps(summary, indent=2))
        return 2 if summary["failed"] or summary["needs_review"] else 0
    except (FlashDataError, ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Stopped waiting. Keep the run directory; collect the saved job later.", file=sys.stderr
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
