#!/usr/bin/env python3
"""
Hermes single-phase evaluation: one hermes invocation does both
task execution AND verification, avoiding the agent-browser ERR_ABORTED
issue in the two-phase Codex evaluator approach.
"""
import json, subprocess, os, datetime, re, sys
from pathlib import Path

sys.stdout.reconfigure(line_buffering=True)
print("=== Hermes single-phase eval starting ===", flush=True)

try:
    import yaml
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "pyyaml", "-q"])
    import yaml

run_dir = Path(os.environ["RUN_DIR"])
cases_file = Path("/tmp/hermes-eval-cases.json")
if not cases_file.exists():
    print(f"ERROR: {cases_file} not found!", flush=True)
    sys.exit(1)

cases = json.loads(cases_file.read_text())
repo_root = Path.cwd()
model_flag = os.environ.get("HERMES_MODEL", "")
print(f"RUN_DIR={run_dir} Cases={len(cases)}", flush=True)


def now():
    return datetime.datetime.now(datetime.timezone.utc)


def run_hermes(prompt, timeout=900, label="orch", cwd=None):
    cmd = ["hermes", "chat", "--yolo", "--quiet", "-q", prompt]
    if model_flag:
        cmd.extend(["--model", model_flag])
    print(f"  [{label}] hermes chat -q (cwd={cwd}, timeout={timeout}s)")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ}, cwd=cwd)
        return r.stdout, r.returncode, r.stderr
    except subprocess.TimeoutExpired:
        print(f"  [{label}] TIMEOUT {timeout}s")
        return "", -1, f"TIMEOUT after {timeout}s"


def setup_workspace(cid):
    ws = Path(f"/tmp/hermes-eval-{cid}")
    ws.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["bash", ".agents/skills/skills-evaluation/scripts/create_case_workspace.sh",
         str(repo_root), str(ws), cid, "--target", os.environ.get("TARGET_ID", "agora")],
        capture_output=True, text=True)
    attempt_ws = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else str(ws)
    if r.returncode != 0:
        print(f"Workspace script failed (exit={r.returncode})")
        attempt_ws = str(ws / cid / "attempt-01")
        os.makedirs(attempt_ws, exist_ok=True)
        src = str(repo_root / ".agents")
        dst = os.path.join(attempt_ws, ".agents")
        subprocess.run(["cp", "-rL", src, dst], capture_output=True)
    return attempt_ws


def build_prompt(case, attempt_ws, assertions_text, cid):
    return (
        f"You are an orchestrator agent with TWO jobs.\n\n"
        f"## JOB 1: Execute the task\n\n"
        f"Workspace: {attempt_ws}\n\n"
        f"Before starting, read the skill docs:\n"
        f"  1. {attempt_ws}/.agents/skills/agora/SKILL.md\n"
        f"  2. Follow its routing instructions for the right product reference.\n\n"
        f'User request:\n"{case["user_prompt"]}"\n\n'
        f"Rules:\n"
        f"- Work only inside {attempt_ws}.\n"
        f"- AGORA_APP_ID and AGORA_APP_CERTIFICATE env vars are set. Use their literal values\n"
        f"  (echo $AGORA_APP_ID) when writing config files. Do NOT write ${{AGORA_APP_ID}} syntax.\n"
        f"- If git clone fails, use: curl -L https://github.com/OWNER/REPO/archive/refs/heads/main.tar.gz | tar xz\n"
        f"- Start dev servers as background processes (nohup pnpm dev > /dev/null 2>&1 &).\n"
        f"- Verify the server is listening (curl -I http://localhost:3000) before moving on.\n\n"
        f"## JOB 2: Verify the result\n\n"
        f"After JOB 1, check these assertions:\n{assertions_text}\n\n"
        f"Verification approach:\n"
        f"- Check cloned repo directory exists with expected files\n"
        f"- Check .env.local has real Agora credentials (not placeholders)\n"
        f"- Check port 3000 is listening (lsof -i :3000 or curl -I http://localhost:3000)\n"
        f"- For browser check: curl http://localhost:3000 and verify HTML contains page content.\n"
        f"  Do NOT use agent-browser or Playwright. curl with HTTP 200 + valid HTML = pass.\n\n"
        f"## OUTPUT\n\n"
        f"End your response with exactly:\n\n"
        f"VERIFICATION_JSON:\n"
        f'{{"case_id": "{cid}", "status": "pass or fail", '
        f'"assertions": [{{"summary": "...", "status": "pass or fail", "evidence": ["..."]}}], '
        f'"notes": ["..."]}}\n\n'
        f'"status" = "pass" only if ALL assertions pass.\n'
        f"curl 200 + valid HTML body = browser check pass (no Playwright needed).\n"
    )


def parse_judgment(stdout, cid):
    json_source = stdout
    if "VERIFICATION_JSON:" in stdout:
        json_source = stdout.split("VERIFICATION_JSON:", 1)[1].strip()
    m = re.search(r'\{[\s\S]*\}', json_source)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    for line in json_source.split("\n"):
        line = line.strip()
        if line.startswith("{") and "case_id" in line:
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
    return None


# === Main loop ===
for case in cases:
    cid = case["case_id"]
    print(f"\n{'='*60}\nCase: {cid}\n{'='*60}")

    attempt_ws = setup_workspace(cid)
    print(f"Workspace: {attempt_ws}")

    case_data = yaml.safe_load(open(case["path"]))
    assertions_text = json.dumps(
        case_data.get("assert", {}).get("required", []), indent=2)

    t_start = now()
    print(f"\n--- Orchestrator ({t_start.isoformat()}) ---", flush=True)

    prompt = build_prompt(case, attempt_ws, assertions_text, cid)
    stdout, exitcode, stderr = run_hermes(prompt, timeout=900, cwd=attempt_ws)

    t_end = now()
    t_dur = (t_end - t_start).total_seconds()
    print(f"Done in {t_dur:.0f}s (exit={exitcode})")

    art_dir = run_dir / "case-artifacts" / cid
    art_dir.mkdir(parents=True, exist_ok=True)
    (art_dir / "orchestrator-raw.txt").write_text(stdout)
    if stderr:
        (art_dir / "orchestrator-stderr.txt").write_text(stderr)

    task_text = stdout
    if "VERIFICATION_JSON:" in stdout:
        task_text = stdout.split("VERIFICATION_JSON:")[0].strip()
    (art_dir / "final-answer.txt").write_text(task_text + "\n")

    print(f"Response (first 500):\n{stdout[:500]}")

    ws_files = subprocess.run(
        ["find", attempt_ws, "-type", "f", "-maxdepth", "4"],
        capture_output=True, text=True).stdout

    case_result = {
        "case_id": cid, "status": "blocked",
        "blocked_reason": "parse-error", "assertions": [],
        "notes": ["Could not parse orchestrator output"],
        "started_at": t_start.isoformat(),
        "completed_at": t_end.isoformat(),
        "total_duration_s": round(t_dur),
        "workspace_root": attempt_ws,
        "mode": "hermes-single-phase",
    }

    parsed = parse_judgment(stdout, cid)
    if parsed:
        case_result.update({
            "status": parsed.get("status", "blocked"),
            "assertions": parsed.get("assertions", []),
            "notes": parsed.get("notes", []),
            "blocked_reason": None,
        })

    (run_dir / "case-results" / f"{cid}.json").write_text(
        json.dumps(case_result, indent=2) + "\n")

    evidence = {
        "orchestrator_output": stdout[:50000],
        "orchestrator_stderr": (stderr or "")[:10000],
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
