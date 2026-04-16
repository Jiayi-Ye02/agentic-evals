#!/usr/bin/env python3
"""Write accepted-session.json from a Codex child session JSONL without semantic normalization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write accepted-session.json from a Codex child session JSONL without semantic normalization."
    )
    parser.add_argument("session_path", help="Path to the accepted Codex child session JSONL")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to stdout when omitted.",
    )
    return parser.parse_args()


def load_raw_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"invalid JSON at {path}:{line_no}: {exc}") from exc
    return events


def main() -> int:
    args = parse_args()
    session_path = Path(args.session_path).resolve()
    raw_events = load_raw_events(session_path)
    accepted = {
        "runtime": "codex",
        "format": "raw-event-stream",
        "authoritative_artifact": str(session_path),
        "derived": False,
        "items": [
            {
                "id": f"msg-{index}",
                "raw": raw,
            }
            for index, raw in enumerate(raw_events, start=1)
        ],
    }

    rendered = json.dumps(accepted, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
