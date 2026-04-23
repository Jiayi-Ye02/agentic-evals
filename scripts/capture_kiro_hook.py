#!/usr/bin/env python3
"""Append one Kiro hook event from STDIN to a JSONL trace file."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Append one Kiro hook event from STDIN to a JSONL trace file."
    )
    parser.add_argument(
        "--output",
        help="Destination raw-hook-trace.jsonl path. Defaults to $KIRO_HOOK_TRACE_PATH.",
    )
    parser.add_argument(
        "--annotate-capture-time",
        action="store_true",
        help="Add a capture_timestamp field when the incoming payload does not include one.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or os.environ.get("KIRO_HOOK_TRACE_PATH")
    if not output:
        print("capture_kiro_hook.py: missing --output or KIRO_HOOK_TRACE_PATH", file=sys.stderr)
        return 1

    raw_input = sys.stdin.read()
    if not raw_input.strip():
        print("capture_kiro_hook.py: stdin was empty", file=sys.stderr)
        return 1

    try:
        payload = json.loads(raw_input)
    except json.JSONDecodeError as exc:
        print(f"capture_kiro_hook.py: invalid JSON from stdin: {exc}", file=sys.stderr)
        return 1

    if args.annotate_capture_time and "capture_timestamp" not in payload:
        from datetime import datetime, timezone

        payload["capture_timestamp"] = datetime.now(timezone.utc).isoformat()

    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
