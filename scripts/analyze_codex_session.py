#!/usr/bin/env python3
"""Extract isolation and answer evidence from a Codex child session JSONL."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


READ_PATTERNS = [
    re.compile(r"""sed\s+-n\s+['"][^'"]*['"]\s+(.+)$"""),
    re.compile(r"""cat\s+(.+)$"""),
    re.compile(r"""nl\s+-ba\s+(.+)$"""),
]

WRITE_PATTERNS = [
    re.compile(r"""(?:^|\s)>>?\s*(.+)$"""),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a Codex child session for skill-eval isolation checks."
    )
    parser.add_argument("session_path", help="Path to the child session JSONL")
    parser.add_argument(
        "--workspace-root",
        required=True,
        help="Expected isolated case workspace root",
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


def extract_paths(command: str, workdir: str | None) -> tuple[list[str], list[str]]:
    reads: list[str] = []
    writes: list[str] = []

    for pattern in READ_PATTERNS:
        match = pattern.search(command)
        if match:
            path = normalize_path(match.group(1), workdir)
            if path:
                reads.append(path)

    for pattern in WRITE_PATTERNS:
        match = pattern.search(command)
        if match:
            path = normalize_path(match.group(1), workdir)
            if path:
                writes.append(path)

    return reads, writes


def main() -> int:
    args = parse_args()
    workspace_root = os.path.realpath(args.workspace_root)
    session_path = Path(args.session_path).resolve()

    lines = session_path.read_text(encoding="utf-8").splitlines()
    session_meta_cwd = None
    final_answer = None
    tool_calls = []
    violations = []

    for line_no, line in enumerate(lines, start=1):
        obj = json.loads(line)
        if obj.get("type") == "session_meta":
            session_meta_cwd = obj.get("payload", {}).get("cwd")
            continue

        if obj.get("type") != "response_item":
            continue

        payload = obj.get("payload", {})
        if payload.get("type") == "function_call":
            if payload.get("name") != "exec_command":
                continue
            try:
                arguments = json.loads(payload.get("arguments", "{}"))
            except json.JSONDecodeError:
                arguments = {}
            workdir = arguments.get("workdir")
            cmd = arguments.get("cmd", "")
            norm_workdir = os.path.realpath(workdir) if workdir else None
            reads, writes = extract_paths(cmd, norm_workdir)
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
                        "command": cmd,
                        "outside": outside,
                    }
                )
            tool_calls.append(
                {
                    "line": line_no,
                    "command": cmd,
                    "workdir": norm_workdir,
                    "reads": reads,
                    "writes": writes,
                }
            )
            continue

        if payload.get("type") == "message" and payload.get("phase") == "final_answer":
            texts = [
                item.get("text", "")
                for item in payload.get("content", [])
                if item.get("type") == "output_text"
            ]
            final_answer = "".join(texts).strip()

    report = {
        "session_path": str(session_path),
        "workspace_root": workspace_root,
        "session_meta_cwd": session_meta_cwd,
        "session_meta_cwd_inside_workspace": path_inside(
            workspace_root, os.path.realpath(session_meta_cwd) if session_meta_cwd else None
        ),
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
