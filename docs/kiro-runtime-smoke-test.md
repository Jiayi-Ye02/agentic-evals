# Kiro Runtime Smoke Test

This note describes the smallest real Kiro runtime test for `skill-eval`.

The preferred path is now direct execution from the current Codex evaluator.
Codex should extract the case `input.user_prompt`, create or reuse the isolated
case workspace, launch Kiro directly, and then judge from the emitted artifacts.

Important runtime note:

- If the case asks Kiro to leave a dev server running after the chat ends, the runtime
  prompt should steer Kiro away from a plain `nohup ... &` launch.
- Prefer a detached launcher such as `python3 -c` with `subprocess.Popen(..., start_new_session=True)`
  so the server can survive after the Kiro session reaches `stop`.

Use it when you want to verify that:

- Kiro can run inside an isolated case workspace
- hooks append raw events to `raw-hook-trace.jsonl`
- `accepted-session.json` can be written from that raw trace as the canonical judge artifact

## Inputs

You need:

- a workspace that contains `.agents/skills/`
- `kiro-cli` on `PATH`
- a prompt file
- a case-artifacts directory for the raw trace and final answer

## One-shot command

```bash
python3 scripts/write_kiro_hook_agent.py "<workspace>" --target-id "<target_id>" >/dev/null
mkdir -p "<case-artifacts>/<case_id>"
: > "<case-artifacts>/<case_id>/raw-hook-trace.jsonl"
: > "<case-artifacts>/<case_id>/final-answer.txt"
mkdir -p "<workspace>/.kiro-runtime"
: > "<workspace>/.kiro-runtime/dev-server.log"
export KIRO_HOOK_TRACE_PATH="<case-artifacts>/<case_id>/raw-hook-trace.jsonl"
(
  cd "<workspace>"
  kiro-cli chat \
    --no-interactive \
    --agent skill-eval-kiro-runtime \
    --trust-all-tools \
    "$(cat "<prompt-file>")"
) > "<case-artifacts>/<case_id>/final-answer.txt"
python3 scripts/normalize_kiro_hook_trace.py \
  "<case-artifacts>/<case_id>/raw-hook-trace.jsonl" \
  --output "<case-artifacts>/<case_id>/accepted-session.json"
```

This direct flow will:

1. write a local `.kiro/agents/skill-eval-kiro-runtime.json`
2. set `KIRO_HOOK_TRACE_PATH`
3. run `kiro-cli chat --no-interactive --agent skill-eval-kiro-runtime --trust-all-tools`
4. capture stdout into `final-answer.txt`
5. write `accepted-session.json` from the raw hook trace

The Kiro runtime prompt is stored in:

- `docs/kiro-runtime-agent-prompt.txt`

Tweak that prompt when you want Kiro to change its runtime behavior without
reintroducing orchestration wrapper scripts.

## Follow-up checks

After the run, inspect:

- `raw-hook-trace.jsonl`
- `final-answer.txt`
- `accepted-session.json`

Then analyze isolation with:

```bash
python3 scripts/analyze_kiro_hook_trace.py \
  "<case-artifacts>/<case_id>/raw-hook-trace.jsonl" \
  --workspace-root "<workspace>" \
  --final-answer-path "<case-artifacts>/<case_id>/final-answer.txt"
```
