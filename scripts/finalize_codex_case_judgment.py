#!/usr/bin/env python3
"""Write final evaluation artifacts from a Codex-authored case judgment."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RENDER_CASE_RESULT = (
    REPO_ROOT
    / ".agents"
    / "skills"
    / "skills-evaluation"
    / "scripts"
    / "render_case_result.py"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write final evaluation artifacts from a Codex-authored case judgment."
    )
    parser.add_argument("run_dir", help="Run directory under runs/")
    parser.add_argument("judgment_json", help="Path to Codex-authored judgment JSON")
    return parser.parse_args()


def run_text(cmd: list[str]) -> str:
    import subprocess

    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return proc.stdout.strip()


def write_report(report_path: Path, payload: dict) -> None:
    lines = [
        "# Run Summary",
        "",
        f"- target case: `{payload['case_id']}`",
        f"- status: `{payload['status']}`",
        "",
        "## Case Table",
        "",
        "| case_id | status |",
        "| --- | --- |",
        f"| {payload['case_id']} | {payload['status']} |",
        "",
        "## Failures",
        "",
    ]
    if payload["status"] == "pass":
        lines.append("- None.")
    elif payload["status"] == "blocked":
        lines.append(
            f"- `{payload['case_id']}` was blocked with `{payload['blocked_reason']}`."
        )
    else:
        lines.append(f"- `{payload['case_id']}` failed one or more required assertions.")

    lines.extend(
        [
            "",
            "## Suggested Next Fixes",
            "",
        ]
    )
    if payload.get("suggested_fix_files"):
        for path in payload["suggested_fix_files"][:3]:
            lines.append(f"- `{path}`")
    else:
        lines.append("- None.")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def append_transcript_judgment(transcript_path: Path, payload: dict) -> None:
    existing = transcript_path.read_text(encoding="utf-8") if transcript_path.exists() else ""
    section = [
        "",
        "### Codex Judgment",
        "",
        f"- status: `{payload['status']}`",
        f"- blocked_reason: `{payload['blocked_reason']}`",
        "",
        "#### Assertions",
    ]
    for assertion in payload.get("assertions", []):
        evidence = ", ".join(assertion.get("evidence", [])) or "none"
        section.append(
            f"- `{assertion.get('status')}` {assertion.get('summary')} (evidence: {evidence})"
        )
    transcript_path.write_text(existing.rstrip() + "\n" + "\n".join(section) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    judgment_path = Path(args.judgment_json).expanduser().resolve()
    if not run_dir.exists():
        raise SystemExit(f"run dir does not exist: {run_dir}")
    if not judgment_path.exists():
        raise SystemExit(f"judgment json does not exist: {judgment_path}")

    payload = json.loads(judgment_path.read_text(encoding="utf-8"))
    case_id = payload["case_id"]

    case_result_path = run_dir / "case-results" / f"{case_id}.json"
    run_text([sys.executable, str(RENDER_CASE_RESULT), str(case_result_path), str(judgment_path)])

    append_transcript_judgment(run_dir / "transcript.md", payload)
    write_report(run_dir / "report.md", payload)

    print(
        json.dumps(
            {
                "run_dir": str(run_dir),
                "case_result_path": str(case_result_path),
                "report_path": str(run_dir / "report.md"),
                "transcript_path": str(run_dir / "transcript.md"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
