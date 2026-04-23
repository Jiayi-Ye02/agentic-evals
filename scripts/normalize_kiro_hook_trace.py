#!/usr/bin/env python3
"""Write accepted-session.json from a Kiro raw hook trace without semantic normalization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HOOK_KEYS = ("hook_event_name", "hookEvent", "hook_name", "event", "hook")
TOOL_NAME_KEYS = ("tool_name", "toolName", "name")
TOOL_INPUT_KEYS = ("tool_input", "toolInput", "input", "arguments")
TOOL_RESPONSE_KEYS = ("tool_response", "toolResponse", "response", "output")
PROMPT_KEYS = ("prompt", "user_prompt", "userPrompt", "message", "text")
CWD_KEYS = ("cwd", "workdir")
TIMESTAMP_KEYS = ("timestamp", "time", "created_at", "createdAt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write accepted-session.json from a Kiro raw hook trace without semantic normalization."
    )
    parser.add_argument("raw_trace_path", help="Path to raw-hook-trace.jsonl")
    parser.add_argument(
        "--output",
        help="Optional output path. Defaults to stdout when omitted.",
    )
    return parser.parse_args()


def first_present(*objs: Any, keys: tuple[str, ...]) -> Any:
    for obj in objs:
        if not isinstance(obj, dict):
            continue
        for key in keys:
            if key in obj and obj[key] not in (None, ""):
                return obj[key]
    return None


def wrap_raw_item(raw: dict[str, Any], index: int) -> dict[str, Any]:
    payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
    hook_name = first_present(raw, payload, keys=HOOK_KEYS) or "unknown"
    timestamp = first_present(raw, payload, keys=TIMESTAMP_KEYS)
    cwd = first_present(raw, payload, keys=CWD_KEYS)
    return {
        "id": f"msg-{index}",
        "hook_event": hook_name,
        "timestamp": timestamp,
        "cwd": cwd,
        "raw": raw,
    }


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
    raw_trace_path = Path(args.raw_trace_path).resolve()
    raw_events = load_raw_events(raw_trace_path)

    items = [wrap_raw_item(raw, index) for index, raw in enumerate(raw_events, start=1)]

    accepted = {
        "runtime": "kiro",
        "format": "raw-hook-trace",
        "authoritative_artifact": str(raw_trace_path),
        "derived": False,
        "items": items,
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
