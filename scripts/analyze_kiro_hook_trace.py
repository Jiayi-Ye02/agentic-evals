#!/usr/bin/env python3
"""Extract isolation and answer evidence from a Kiro raw hook trace JSONL."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

from normalize_kiro_hook_trace import first_present


READ_PATTERNS = [
    re.compile(r"""sed\s+-n\s+['"][^'"]*['"]\s+(.+)$"""),
    re.compile(r"""cat\s+(.+)$"""),
    re.compile(r"""nl\s+-ba\s+(.+)$"""),
    re.compile(r"""rg\s+.+\s+(.+)$"""),
]

WRITE_PATTERNS = [
    re.compile(r"""(?<!\d)>>?\s*("([^"]+)"|'([^']+)'|[^\s&;]+)"""),
]

HOOK_KEYS = ("hook_event_name", "hookEvent", "hook_name", "event", "hook")
TOOL_NAME_KEYS = ("tool_name", "toolName", "name")
TOOL_INPUT_KEYS = ("tool_input", "toolInput", "input", "arguments")
TOOL_RESPONSE_KEYS = ("tool_response", "toolResponse", "response", "output")
CWD_KEYS = ("cwd", "workdir")
FINAL_ANSWER_KEYS = (
    "final_answer",
    "finalAnswer",
    "assistant_response",
    "assistantResponse",
    "output_text",
    "text",
    "message",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a Kiro raw hook trace for skill-eval isolation checks."
    )
    parser.add_argument("raw_trace_path", help="Path to raw-hook-trace.jsonl")
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Expected isolated case workspace root",
    )
    parser.add_argument(
        "--final-answer-path",
        help="Optional path to final-answer.txt for filling final_answer when the trace lacks it.",
    )
    return parser.parse_args()


def normalize_path(value: str, workdir: str | None) -> str | None:
    value = value.strip().strip("'\"")
    if not value or value.startswith("-") or value.startswith("http"):
        return None
    if value in {"/dev/null", "/dev/stdout", "/dev/stderr"} or value.startswith("/dev/fd/"):
        return None
    if value.startswith("`") and value.endswith("`"):
        value = value[1:-1]
    if value.startswith("./") or value.startswith("../") or not value.startswith("/"):
        if not workdir:
            return None
        return os.path.realpath(os.path.join(workdir, value))
    return os.path.realpath(value)


def path_inside(root: str, candidate: str | None) -> bool:
    if not candidate:
        return True
    try:
        return os.path.commonpath([root, candidate]) == root
    except ValueError:
        return False


def maybe_paths_from_value(value: Any, workdir: str | None) -> list[str]:
    if isinstance(value, str):
        normalized = normalize_path(value, workdir)
        return [normalized] if normalized else []
    if isinstance(value, list):
        paths: list[str] = []
        for item in value:
            paths.extend(maybe_paths_from_value(item, workdir))
        return paths
    if isinstance(value, dict):
        paths: list[str] = []
        for key in ("path", "paths", "file_path", "filePath", "target", "targets"):
            if key in value:
                paths.extend(maybe_paths_from_value(value[key], workdir))
        if "operations" in value:
            paths.extend(maybe_paths_from_value(value["operations"], workdir))
        return paths
    return []


def extract_paths_from_command(command: str, workdir: str | None) -> tuple[list[str], list[str]]:
    reads: list[str] = []
    writes: list[str] = []

    for pattern in READ_PATTERNS:
        match = pattern.search(command)
        if match:
            path = normalize_path(match.group(1), workdir)
            if path:
                reads.append(path)

    for pattern in WRITE_PATTERNS:
        for match in pattern.finditer(command):
            path = normalize_path(match.group(1), workdir)
            if path:
                writes.append(path)

    return reads, writes


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
    workspace_root = os.path.realpath(args.workspace_root)
    raw_trace_path = Path(args.raw_trace_path).resolve()
    raw_events = load_raw_events(raw_trace_path)

    tool_calls = []
    violations = []
    final_answer = None

    for line_no, raw in enumerate(raw_events, start=1):
        payload = raw.get("payload") if isinstance(raw.get("payload"), dict) else {}
        hook_name = first_present(raw, payload, keys=HOOK_KEYS)
        cwd = first_present(raw, payload, keys=CWD_KEYS)
        tool_name = first_present(raw, payload, keys=TOOL_NAME_KEYS)
        tool_input = first_present(raw, payload, keys=TOOL_INPUT_KEYS) or {}
        tool_response = first_present(raw, payload, keys=TOOL_RESPONSE_KEYS)
        norm_workdir = os.path.realpath(cwd) if isinstance(cwd, str) and cwd else None

        if hook_name == "stop":
            final_answer = first_present(raw, payload, keys=FINAL_ANSWER_KEYS) or final_answer
            continue

        if hook_name not in {"preToolUse", "postToolUse"}:
            continue

        reads: list[str] = []
        writes: list[str] = []
        command = None

        if isinstance(tool_input, dict):
            command = (
                tool_input.get("command")
                or tool_input.get("cmd")
                or tool_input.get("bash_command")
                or tool_input.get("bashCommand")
            )
            reads.extend(maybe_paths_from_value(tool_input.get("read"), norm_workdir))
            reads.extend(maybe_paths_from_value(tool_input.get("reads"), norm_workdir))
            writes.extend(maybe_paths_from_value(tool_input.get("write"), norm_workdir))
            writes.extend(maybe_paths_from_value(tool_input.get("writes"), norm_workdir))
            reads.extend(maybe_paths_from_value(tool_input, norm_workdir))

        if isinstance(command, str):
            cmd_reads, cmd_writes = extract_paths_from_command(command, norm_workdir)
            reads.extend(cmd_reads)
            writes.extend(cmd_writes)

        outside = []
        if norm_workdir and not path_inside(workspace_root, norm_workdir):
            outside.append({"kind": "workdir", "path": norm_workdir})
        for path in reads:
            if not path_inside(workspace_root, path):
                outside.append({"kind": "read", "path": path})
        for path in writes:
            if not path_inside(workspace_root, path):
                outside.append({"kind": "write", "path": path})

        if outside:
            violations.append(
                {
                    "line": line_no,
                    "hook_event": hook_name,
                    "tool_name": tool_name,
                    "outside": outside,
                }
            )

        tool_calls.append(
            {
                "line": line_no,
                "hook_event": hook_name,
                "tool_name": tool_name,
                "workdir": norm_workdir,
                "command": command,
                "reads": sorted(set(reads)),
                "writes": sorted(set(writes)),
                "tool_response": tool_response,
            }
        )

    if not final_answer and args.final_answer_path:
        final_answer_path = Path(args.final_answer_path).resolve()
        if final_answer_path.exists():
            final_answer = final_answer_path.read_text(encoding="utf-8").strip() or None

    report = {
        "trace_path": str(raw_trace_path),
        "workspace_root": workspace_root,
        "observed_tool_workdirs": [call["workdir"] for call in tool_calls if call["workdir"]],
        "observed_tool_calls": tool_calls,
        "isolation_violations": violations,
        "isolation_pass": len(tool_calls) > 0 and not violations,
        "final_answer": final_answer,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
