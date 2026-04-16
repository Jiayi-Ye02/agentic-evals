# Session Evidence Contract

This document defines the evidence sources used by `agentic-evals`.

The evaluator runtime is Codex.
It supports two execution runtimes:

- Codex local session store
- Kiro raw hook traces

The evaluator should pick the execution runtime that is actually available in the current environment and record it in:

- `manifest.json.evaluator_runtime` with value `codex`
- `manifest.json.execution_runtime` with value `codex` or `kiro`
- `manifest.json.evidence_mode` with value `codex-local-session-store` or `kiro-hook-trace`

## Primary Sources

Use these sources in priority order:

- authoritative runtime-native evidence from the active execution runtime
- accepted final answer extracted from that runtime evidence or the runtime's final output capture
- runtime-native locator metadata

Per runtime:

- Codex execution:
  - accepted child session under `~/.codex/sessions/`
  - `spawn_agent` success metadata such as nickname or returned id
  - `~/.codex/state_5.sqlite` only to locate and disambiguate child threads
- Kiro execution:
  - newline-delimited raw hook trace at `case-artifacts/<case_id>/raw-hook-trace.jsonl`
  - Kiro process metadata such as exit status, case workspace, and run start time
  - any final-answer capture written by the driver to `case-artifacts/<case_id>/final-answer.txt`

Do not treat the execution subject's self-reported `TRACE_FILES_READ`, `TRACE_COMMANDS_EXECUTED`, or similar summaries as authoritative evidence.
They are only low-confidence supporting notes.

`accepted-session.json` is the canonical case artifact that stores the raw accepted evidence for both runtimes.
For Kiro it should be written directly from `raw-hook-trace.jsonl` without semantic normalization.

## Attempt Evidence Location

The evaluator should identify the accepted evidence for a case attempt by combining:

- runtime-native spawn metadata
- attempt start time
- case workspace path
- thread title, nickname, or label as tie-breakers when the runtime exposes them
- session cwd metadata only as a low-confidence locator when the runtime may inherit the parent cwd

Per runtime:

- Codex execution:
  - `spawn_agent` success metadata such as nickname or returned id when available
  - child session `session_meta.payload.source.subagent.thread_spawn.parent_thread_id`
  - `~/.codex/state_5.sqlite` `thread_spawn_edges` when available
- Kiro execution:
  - the evaluator-selected `case-artifacts/<case_id>/raw-hook-trace.jsonl` path
  - the case workspace recorded in the hook payload or wrapper metadata
  - Kiro run start and stop timestamps
  - the driver command or wrapper metadata that launched Kiro for that case

If the evaluator cannot reliably identify a single authoritative evidence source for the case attempt, mark the case `blocked`.

## What To Extract From Session Evidence

The evaluator may analyze runtime-native evidence in memory with records such as:

- `session_start`
- `user_prompt`
- `tool_call`
- `tool_result`
- `tool_workdir_observed`
- `command_observed`
- `file_read_observed`
- `file_write_observed`
- `final_answer`
- `session_end`

These records are sufficient to judge many cases because they expose the child prompt, tool calls, tool outputs, and final answer.
This common judgment model is optional evaluator logic. It does not replace the raw evidence stored in `accepted-session.json`.

Runtime notes:

- Codex evidence originates as JSONL and should be copied into `accepted-session.json` as ordered raw entries.
- Kiro evidence originates as raw hook JSONL and should be copied into `accepted-session.json` as ordered raw entries.
- helper scripts are available at:
  - `scripts/export_codex_session_to_accepted.py`
  - `scripts/normalize_kiro_hook_trace.py`
  - `scripts/analyze_kiro_hook_trace.py`

## Extraction Rules

- Convert Codex `session_meta` into `session_start`.
- Convert Codex `task_complete` or Kiro `stop` into `session_end`.
- Convert Codex `response_item.function_call` or Kiro `preToolUse` into `tool_call`.
- Convert Codex `response_item.function_call_output` or Kiro `postToolUse` into `tool_result`.
- When a tool call or hook payload includes `workdir` or `cwd`, emit `tool_workdir_observed`.
- When a tool result shows an executed shell command, emit `command_observed`.
- When a command or tool payload clearly reads a file, emit `file_read_observed`.
- When a command, patch, or tool payload clearly writes a file, emit `file_write_observed`.
- Convert the accepted final assistant output into `final_answer`.

For shell-derived file observations, prefer stable patterns such as:

- `sed -n ... <path>`
- `cat <path>`
- `nl -ba <path>`
- `rg ... <path>`
- `find ...`

If a path cannot be reconstructed reliably, do not invent one.

For Kiro raw hook traces:

- preserve each raw hook event as one JSON line
- prefer hook names such as `agentSpawn`, `userPromptSubmit`, `preToolUse`, `postToolUse`, and `stop`
- preserve the hook payload as received on stdin
- if the final user-facing answer is not present in the hook payloads, the evaluator must capture it separately into `final-answer.txt`
- if neither the raw hook trace nor a reliable final-answer capture can support a final-answer assertion, mark that assertion `blocked`

## Isolation Rules

Judge isolation only from observed evidence.

- Prefer per-tool `workdir` values, hook-captured `cwd` values, and command-derived paths as the authoritative isolation signals
- Treat `session_meta.cwd` as advisory only for Codex spawned-subagent runs, because it may remain equal to the parent thread cwd even when the child agent's tool calls stay inside the case workspace
- observed per-tool `workdir` values must stay inside the accepted case workspace
- observed read and write paths must stay inside the accepted case workspace
- if a command such as `pwd` prints a cwd, that observed cwd must stay inside the accepted case workspace
- if observed paths leave the case workspace, emit `isolation_violation`
- do not treat `session_meta.cwd` alone as an isolation violation when all observed tool workdirs and resolved paths stay inside the accepted case workspace
- if no reliable tool workdir, resolved path, or command-derived cwd can be observed, that evidence cannot justify a `pass`

## Artifact Expectations

The evaluator should preserve:

```text
case-artifacts/<case_id>/
├── raw-hook-trace.jsonl  # required when execution_runtime=kiro
├── accepted-session.json
└── final-answer.txt
```

`accepted-session.json` is the accepted raw evidence artifact for the active runtime.
It may be:

- a JSON wrapper that preserves the accepted Codex session JSONL as ordered raw entries, or
- a JSON wrapper that preserves the accepted Kiro raw hook trace as ordered raw entries

For Kiro:

- `raw-hook-trace.jsonl` remains the capture file written during execution
- `accepted-session.json` is the canonical per-case judge artifact written from that raw trace
- assertion evidence may cite either `accepted-session.json#msg-<n>` or `raw-hook-trace.jsonl#L<line>`, depending on which is more direct

## Transcript Rendering

`transcript.md` should be rendered directly from the accepted session evidence, with references back to the accepted session when useful.

It should:

- preserve accepted event order
- identify the thread id and session path
- remain clearly derivative of accepted session evidence
