#!/usr/bin/env python3
"""Write a local Kiro agent config that captures raw hook traces for skill-eval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


DEFAULT_AGENT_NAME = "skill-eval-kiro-runtime"
DEFAULT_PROMPT_TEMPLATE = (
    Path(__file__).resolve().parents[1] / "docs" / "kiro-runtime-agent-prompt.txt"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a local Kiro agent config that captures raw hook traces for skill-eval."
    )
    parser.add_argument("workspace", help="Case workspace root where Kiro will run")
    parser.add_argument(
        "--agent-name",
        default=DEFAULT_AGENT_NAME,
        help=f"Agent name to write (default: {DEFAULT_AGENT_NAME})",
    )
    parser.add_argument(
        "--capture-script",
        help="Absolute path to capture_kiro_hook.py. Defaults to this repo's script path.",
    )
    parser.add_argument(
        "--prompt-template",
        help="Absolute path to the Kiro runtime prompt template. Defaults to docs/kiro-runtime-agent-prompt.txt.",
    )
    parser.add_argument(
        "--target-id",
        help="Optional target id to narrow resources to .agents/skills/<target_id>/SKILL.md",
    )
    return parser.parse_args()


def build_agent_config(
    workspace: Path,
    capture_script: Path,
    prompt_template: Path,
    agent_name: str,
    target_id: str | None,
) -> dict:
    runtime_dir = (workspace / ".kiro-runtime").resolve()
    dev_server_log_path = (runtime_dir / "dev-server.log").resolve()
    resource_glob = (
        str((workspace / ".agents" / "skills" / target_id / "SKILL.md").resolve())
        if target_id
        else str((workspace / ".agents" / "skills" / "**" / "SKILL.md").resolve())
    )
    hook_command = (
        f'python3 "{capture_script}" --annotate-capture-time --output "$KIRO_HOOK_TRACE_PATH"'
    )
    prompt_text = prompt_template.read_text(encoding="utf-8")
    prompt_text = prompt_text.replace("{{RUNTIME_DIR}}", str(runtime_dir))
    prompt_text = prompt_text.replace("{{DEV_SERVER_LOG_PATH}}", str(dev_server_log_path))
    return {
        "name": agent_name,
        "description": "Kiro runtime agent for skill-eval with raw hook trace capture.",
        "prompt": prompt_text,
        "tools": [
            "read",
            "write",
            "shell",
        ],
        "allowedTools": [
            "read",
            "write",
            "shell",
        ],
        "resources": [
            f"skill://{resource_glob}",
        ],
        "hooks": {
            "agentSpawn": [{"command": hook_command}],
            "userPromptSubmit": [{"command": hook_command}],
            "preToolUse": [{"matcher": "*", "command": hook_command}],
            "postToolUse": [{"matcher": "*", "command": hook_command}],
            "stop": [{"command": hook_command}],
        },
    }


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists():
        raise SystemExit(f"workspace does not exist: {workspace}")

    capture_script = (
        Path(args.capture_script).expanduser().resolve()
        if args.capture_script
        else Path(__file__).resolve().parent / "capture_kiro_hook.py"
    )
    if not capture_script.exists():
        raise SystemExit(f"capture script does not exist: {capture_script}")

    prompt_template = (
        Path(args.prompt_template).expanduser().resolve()
        if args.prompt_template
        else DEFAULT_PROMPT_TEMPLATE
    )
    if not prompt_template.exists():
        raise SystemExit(f"prompt template does not exist: {prompt_template}")

    agent_dir = workspace / ".kiro" / "agents"
    agent_dir.mkdir(parents=True, exist_ok=True)
    agent_path = agent_dir / f"{args.agent_name}.json"
    config = build_agent_config(
        workspace,
        capture_script,
        prompt_template,
        args.agent_name,
        args.target_id,
    )
    agent_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(agent_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
