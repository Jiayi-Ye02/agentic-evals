# Session Evidence Contract

This document defines the local evidence sources used by `agentic-evals`.

The current evaluator model relies on Codex local session logs rather than a dedicated platform trace API.

## Primary Sources

Use these sources in priority order:

- accepted fresh-agent session JSONL under `~/.codex/sessions/`
- accepted final answer extracted from the child session
- `~/.codex/state_5.sqlite` only to locate and disambiguate child threads

Do not treat the fresh agent's self-reported `TRACE_FILES_READ` or `TRACE_COMMANDS_EXECUTED` as authoritative evidence.
They may appear in older child sessions, but they are only low-confidence supporting notes.

## Child Session Location

The evaluator should identify the accepted child session by combining:

- `spawn_agent` success metadata such as nickname or returned id when available
- child session `session_meta.payload.source.subagent.thread_spawn.parent_thread_id`
- start time relative to the case attempt
- thread title, cwd, or nickname as tie-breakers
- `~/.codex/state_5.sqlite` `thread_spawn_edges` when available

If the evaluator cannot reliably identify a single child session for the case attempt, mark the case `blocked`.

## What To Extract From Session JSONL

The evaluator may use these session JSONL item types:

- `session_meta`
- `event_msg.user_message`
- `event_msg.agent_message`
- `event_msg.task_started`
- `event_msg.task_complete`
- `response_item.function_call`
- `response_item.function_call_output`
- `response_item.message`

These records are sufficient to judge many cases because they expose the child prompt, tool calls, tool outputs, and final answer.

## Extraction Rules

- Convert `session_meta` into `session_start`.
- Convert `task_complete` into `session_end`.
- Convert `response_item.function_call` into `tool_call`.
- Convert `response_item.function_call_output` into `tool_result`.
- When a tool result shows an executed shell command, emit `command_observed`.
- When a command clearly reads a file, emit `file_read_observed`.
- When a command or patch clearly writes a file, emit `file_write_observed`.
- Convert the accepted child-session final assistant output into `final_answer`.

For shell-derived file observations, prefer stable patterns such as:

- `sed -n ... <path>`
- `cat <path>`
- `nl -ba <path>`
- `rg ... <path>`
- `find ...`

If a path cannot be reconstructed reliably, do not invent one.

## Isolation Rules

Judge isolation only from observed evidence.

- observed `cwd` values must stay inside the accepted case workspace
- observed read and write paths must stay inside the accepted case workspace
- if observed paths leave the case workspace, emit `isolation_violation`
- if no reliable path or cwd can be observed, that evidence cannot justify a `pass`

## Artifact Expectations

The evaluator should preserve:

```text
case-artifacts/<case_id>/
├── accepted-session.jsonl
└── final-answer.txt
```

`accepted-session.jsonl` is the copied child session evidence.

## Transcript Rendering

`transcript.md` should be rendered directly from the accepted session evidence, with references back to the accepted session when useful.

It should:

- preserve accepted event order
- identify the thread id and session path
- remain clearly derivative of accepted session evidence
