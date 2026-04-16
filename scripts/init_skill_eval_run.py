#!/usr/bin/env python3
"""Canonical entrypoint for initializing skill-eval run scaffolds.

This wrapper intentionally hides the historical implementation filename under
`.agents/skills/skills-evaluation/scripts/`.
"""

from __future__ import annotations

from pathlib import Path
import runpy
import sys


def main() -> None:
    target = (
        Path(__file__).resolve().parents[1]
        / ".agents"
        / "skills"
        / "skills-evaluation"
        / "scripts"
        / "run_openclaw_case_eval.py"
    )
    if not target.exists():
        raise SystemExit(f"missing delegated script: {target}")
    sys.argv[0] = str(Path(__file__).resolve())
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
