#!/usr/bin/env python3
"""Two-phase OpenClaw evaluation via acpx: task agent + evaluator agent."""
import json, subprocess, os, datetime, yaml, re, sys
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
cases = json.loads(Path("/tmp/eval-cases.json").read_text())
repo_root = Path.cwd()

def now():
    return datetime.datetime.now(datetime.timezone.utc)

def run_openclaw(prompt, timeout=600):
    """Run a prompt via acpx openclaw exec, return (stdout_text, exit_code)."""
    cmd = ["acpx", "--approve-all", "--format", "json", "openclaw", "exec", prompt]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=None, text=True, timeout=timeout)
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {timeout}s")
        return json.dumps({"error": f"TIMEOUT after {timeout}s"}), -1

def extract_response_text(raw_json):
    """Extract the agent's text response from acpx NDJSON output."""
    text_parts = []
    for line in raw_json.strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            params = msg.get("params", {})
            update = params.get("update", {})
            if update.get("sessionUpdate") == "agent_message_chunk":
                content = update.get("content", {})
                if content.get("type") == "text":
                    text_parts.append(content.get("text", ""))
        except:
            continue
    return "".join(text_parts)

def extract_tool_calls(raw_json):
    """Extract tool call info from acpx NDJSON output."""
    tools = []
    for line in raw_json.strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            params = msg.get("params", {})
            update = params.get("update", {})
            if update.get("sessionUpdate") in ("tool_call_start", "tool_call"):
                tools.append(update)
        except:
            continue
    return tools

for case in cases:
    cid = case["case_id"]
    print(f"\n{'='*60}")
    print(f"Case: {cid}")
    print(f"{'='*60}")

    # Create workspace
    ws = Path(f"/tmp/openclaw-eval-{cid}")
    ws.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["bash", ".agents/skills/skills-evaluation/scripts/create_case_workspace.sh",
         str(repo_root), str(ws), cid, "--target", os.environ.get("TARGET_ID", "agora")],
        capture_output=True, text=True)
    attempt_ws = result.stdout.strip() or str(ws)
    print(f"Workspace: {attempt_ws}")

    # --- Phase 1: Task Agent ---
    t1_start = now()
    print(f"\n--- Phase 1: Task Agent ({t1_start.isoformat()}) ---")

    task_prompt = (
        f"You are working in workspace: {attempt_ws}\n\n"
        f"Task: answer this user request naturally, using the workspace as needed:\n"
        f'"{case["user_prompt"]}"\n\n'
        f"Requirements:\n"
        f"- Treat {attempt_ws} as your only workspace.\n"
        f"- Keep all file reads, writes, and shell commands inside it.\n"
        f"- Use the skill docs in .agents/skills/ if relevant.\n"
        f"- Give the exact answer you would send to the user."
    )

    task_raw, task_exit = run_openclaw(task_prompt)
    t1_end = now()
    t1_dur = (t1_end - t1_start).total_seconds()
    print(f"Phase 1 completed in {t1_dur:.0f}s (exit={task_exit})")

    art_dir = run_dir / "case-artifacts" / cid
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "task-agent-raw.json").write_text(task_raw)

    task_response = extract_response_text(task_raw)
    task_tools = extract_tool_calls(task_raw)
    print(f"Phase 1 response (first 500):\n{task_response[:500]}")
    print(f"Phase 1 tool calls: {len(task_tools)}")
    (art_dir / "final-answer.txt").write_text(task_response + "\n")

    # Workspace state
    ws_files = subprocess.run(
        ["find", attempt_ws, "-type", "f", "-maxdepth", "4"],
        capture_output=True, text=True).stdout
    print(f"Workspace files:\n{ws_files[:500]}")

    # --- Phase 2: Evaluator Agent ---
    t2_start = now()
    print(f"\n--- Phase 2: Evaluator ({t2_start.isoformat()}) ---")

    case_data = yaml.safe_load(open(case["path"]))
    assertions_text = json.dumps(case_data.get("assert", {}).get("required", []), indent=2)

    eval_prompt = (
        "You are an independent evaluator judging a DIFFERENT agent's work.\n"
        "Do NOT execute commands. Only read evidence and judge.\n\n"
        f"Task prompt given to the agent:\n---\n{case['user_prompt']}\n---\n\n"
        f"Agent response:\n---\n{task_response}\n---\n\n"
        f"Agent used {len(task_tools)} tool calls.\n\n"
        f"Files in workspace after agent ran:\n{ws_files}\n\n"
        f"Assertions to judge:\n{assertions_text}\n\n"
        "For each assertion: PASS or FAIL with specific evidence.\n"
        "Output ONLY valid JSON (no markdown wrapping):\n"
        '{"case_id": "' + cid + '", "status": "pass or fail", '
        '"assertions": [{"summary": "...", "status": "pass or fail", "evidence": ["..."]}], '
        '"notes": ["..."]}'
    )

    eval_raw, eval_exit = run_openclaw(eval_prompt, timeout=300)
    t2_end = now()
    t2_dur = (t2_end - t2_start).total_seconds()
    print(f"Phase 2 completed in {t2_dur:.0f}s (exit={eval_exit})")

    (art_dir / "evaluator-raw.json").write_text(eval_raw)

    eval_response = extract_response_text(eval_raw)
    print(f"Phase 2 response (first 800):\n{eval_response[:800]}")

    # Parse judgment
    case_result = {
        "case_id": cid,
        "status": "blocked",
        "blocked_reason": "evaluator-parse-error",
        "assertions": [],
        "notes": ["Could not parse evaluator response"],
        "task_started_at": t1_start.isoformat(),
        "task_completed_at": t1_end.isoformat(),
        "task_duration_s": round(t1_dur),
        "verification_started_at": t2_start.isoformat(),
        "verification_completed_at": t2_end.isoformat(),
        "verification_duration_s": round(t2_dur),
        "total_duration_s": round(t1_dur + t2_dur),
        "workspace_root": attempt_ws,
    }

    json_match = re.search(r'\{[\s\S]*\}', eval_response)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            case_result.update({
                "status": parsed.get("status", "blocked"),
                "assertions": parsed.get("assertions", []),
                "notes": parsed.get("notes", []),
                "blocked_reason": None,
            })
        except Exception as e:
            print(f"Judgment parse error: {e}")

    (run_dir / "case-results" / f"{cid}.json").write_text(
        json.dumps(case_result, indent=2) + "\n")

    # Evidence
    evidence = {
        "task_agent_output": task_raw[:50000],
        "evaluator_output": eval_raw[:50000],
        "workspace_files": ws_files,
    }
    (art_dir / "accepted-session.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n")

    print(f"\n--- Result: {case_result['status']} ---")
    for a in case_result.get("assertions", []):
        print(f"  [{a.get('status','?')}] {a.get('summary','')[:100]}")

print("\nAll cases complete.")
