#!/usr/bin/env python3
"""Two-phase OpenClaw evaluation via acpx: task agent + evaluator agent."""
import json, subprocess, os, datetime, yaml, re, sys
from pathlib import Path

run_dir = Path(os.environ["RUN_DIR"])
cases = json.loads(Path("/tmp/eval-cases.json").read_text())
repo_root = Path.cwd()

def now():
    return datetime.datetime.now(datetime.timezone.utc)

def run_openclaw(prompt, timeout=600, label="agent"):
    """Run a prompt via acpx openclaw exec with isolation."""
    cmd = [
        "acpx", "--approve-all", "--format", "json",
        "openclaw", "exec", prompt,
    ]
    print(f"  [{label}] Running acpx openclaw exec...")
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=None,
            text=True, timeout=timeout,
            env={**os.environ}
        )
        return result.stdout, result.returncode
    except subprocess.TimeoutExpired:
        print(f"  [{label}] TIMEOUT after {timeout}s")
        return json.dumps({"error": f"TIMEOUT after {timeout}s"}), -1

def reset_openclaw_session():
    """Reset the OpenClaw session to ensure evaluator gets a clean context."""
    print("  Resetting OpenClaw session...")
    subprocess.run(
        ["acpx", "--approve-all", "openclaw", "sessions", "new"],
        capture_output=True, text=True, timeout=30
    )
    # Wait for gateway to fully release the previous session
    import time
    time.sleep(5)
    print("  Session reset complete.")

def extract_response_text(raw_json):
    """Extract the agent's text response from acpx NDJSON output."""
    text_parts = []
    for line in raw_json.strip().split("\n"):
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            # Check for agent_message_chunk in session/update
            params = msg.get("params", {})
            update = params.get("update", {})
            if update.get("sessionUpdate") == "agent_message_chunk":
                content = update.get("content", {})
                if content.get("type") == "text":
                    text_parts.append(content.get("text", ""))
            # Also check for direct result with text (some ACP responses)
            result = msg.get("result", {})
            if isinstance(result, dict) and result.get("text"):
                text_parts.append(result["text"])
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
            su = update.get("sessionUpdate", "")
            # OpenClaw uses various tool-related session updates
            if su in ("tool_call_start", "tool_call", "tool_use_start",
                       "tool_use", "tool_result", "tool_output"):
                tools.append({"type": su, "data": update})
        except:
            continue
    return tools

def count_ndjson_events(raw_json):
    """Count total NDJSON lines for diagnostics."""
    return sum(1 for line in raw_json.strip().split("\n") if line.strip())

for case in cases:
    cid = case["case_id"]
    print(f"\n{'='*60}")
    print(f"Case: {cid}")
    print(f"{'='*60}")

    # Create workspace
    # create_case_workspace.sh expects source_workspace to be PARENT of agentic-evals/
    ws = Path(f"/tmp/openclaw-eval-{cid}")
    ws.mkdir(parents=True, exist_ok=True)
    source_ws = repo_root.parent  # parent dir that contains agentic-evals/
    result = subprocess.run(
        ["bash", ".agents/skills/skills-evaluation/scripts/create_case_workspace.sh",
         str(source_ws), str(ws), cid, "--target", os.environ.get("TARGET_ID", "agora")],
        capture_output=True, text=True)
    attempt_ws = result.stdout.strip() or str(ws)
    if result.returncode != 0:
        print(f"Workspace script failed (exit={result.returncode}): {result.stderr[:300]}")
        # Fallback: manually create workspace with skill files
        attempt_ws = str(ws / cid / "attempt-01")
        os.makedirs(attempt_ws, exist_ok=True)
        subprocess.run(["cp", "-r", str(repo_root / ".agents"), attempt_ws], capture_output=True)
        print(f"Fallback: copied .agents/ to {attempt_ws}")
    print(f"Workspace: {attempt_ws}")

    # --- Phase 1: Task Agent ---
    t1_start = now()
    print(f"\n--- Phase 1: Task Agent ({t1_start.isoformat()}) ---")

    # Include env var hint in prompt so agent knows they're available
    task_prompt = (
        f"You are working in workspace: {attempt_ws}\n\n"
        f"IMPORTANT: Before starting, read the skill documentation files in your workspace:\n"
        f"  1. First read: {attempt_ws}/.agents/skills/agora/SKILL.md\n"
        f"  2. Then follow its routing instructions to find the right product reference.\n"
        f"These files contain critical guidance for completing the task correctly.\n\n"
        f"Task: answer this user request naturally, using the workspace as needed:\n"
        f'"{case["user_prompt"]}"\n\n'
        f"Requirements:\n"
        f"- Treat {attempt_ws} as your only workspace.\n"
        f"- Keep all file reads, writes, and shell commands inside it.\n"
        f"- The environment variables AGORA_APP_ID and AGORA_APP_CERTIFICATE are set and available via $AGORA_APP_ID and $AGORA_APP_CERTIFICATE in shell commands.\n"
        f"- Give the exact answer you would send to the user."
    )

    task_raw, task_exit = run_openclaw(task_prompt, timeout=600, label="task")
    t1_end = now()
    t1_dur = (t1_end - t1_start).total_seconds()

    task_events = count_ndjson_events(task_raw)
    print(f"Phase 1 completed in {t1_dur:.0f}s (exit={task_exit}, events={task_events})")

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
    ws_files_short = ws_files[:2000]  # Limit for evaluator prompt
    print(f"Workspace files ({ws_files.count(chr(10))} files):\n{ws_files[:500]}")

    # --- Phase 2: Evaluator Agent ---
    # Reset session so evaluator gets clean context (not polluted by task agent)
    reset_openclaw_session()
    t2_start = now()
    print(f"\n--- Phase 2: Evaluator ({t2_start.isoformat()}) ---")

    case_data = yaml.safe_load(open(case["path"]))
    assertions_text = json.dumps(case_data.get("assert", {}).get("required", []), indent=2)

    # Keep evaluator prompt concise and action-oriented so OpenClaw engages
    eval_prompt = (
        f"Please analyze this agent's work and give me your judgment.\n\n"
        f"The agent was asked to: {case['user_prompt'][:300]}\n\n"
        f"The agent responded:\n{task_response[:1500]}\n\n"
        f"Files in workspace: {ws_files.count(chr(10))}\n\n"
        f"Check these assertions and tell me pass or fail for each:\n{assertions_text}\n\n"
        f"Write your answer as a JSON object with this structure:\n"
        '{"case_id":"' + cid + '","status":"pass or fail",'
        '"assertions":[{"summary":"description","status":"pass or fail","evidence":["what you observed"]}],'
        '"notes":["any observations"]}\n\n'
        "Please write the JSON now."
    )

    eval_raw, eval_exit = run_openclaw(eval_prompt, timeout=300, label="eval")
    t2_end = now()
    t2_dur = (t2_end - t2_start).total_seconds()

    eval_events = count_ndjson_events(eval_raw)
    print(f"Phase 2 completed in {t2_dur:.0f}s (exit={eval_exit}, events={eval_events})")

    (art_dir / "evaluator-raw.json").write_text(eval_raw)

    eval_response = extract_response_text(eval_raw)
    print(f"Phase 2 response (first 800):\n{eval_response[:800]}")

    # If no response text extracted, try to get it from the raw output directly
    if not eval_response.strip():
        print("WARNING: No response text extracted from evaluator. Dumping raw for debug:")
        print(eval_raw[:1000])

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
    for n in case_result.get("notes", []):
        print(f"  note: {n[:200]}")

print("\nAll cases complete.")
