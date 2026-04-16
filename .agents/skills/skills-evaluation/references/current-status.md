# Current Status

`skill-eval` now treats Codex as the evaluator runtime and supports Codex or Kiro as the execution runtime.
Codex CLI support for fresh child-session execution has been validated locally, and Kiro is modeled around raw hook-trace evidence.

## What is ready

- repo contract updated to separate evaluator runtime from execution runtime
- artifact names normalized around `accepted-session.json`, with `raw-hook-trace.jsonl` added as the authoritative Kiro artifact
- Kiro raw-hook-trace evidence flow documented
- helper scaffold script added for deterministic run-directory initialization
- Codex CLI smoke-tested successfully on `codex-cli 0.118.0` with a real parent session, one child session, and a persisted `thread_spawn_edges` link in `~/.codex/state_5.sqlite`

## What still depends on runtime support

A fully automated dynamic evaluation on Codex CLI still requires a live runtime where:

- `spawn_agent` can create fresh subagents successfully
- `~/.codex/sessions` and `~/.codex/state_5.sqlite` are writable and readable
- authentication and network allow live Codex sessions to complete normally

Kiro execution requires a live runtime where:

- the evaluator can launch Kiro inside the isolated case workspace
- hooks can write `raw-hook-trace.jsonl` reliably
- the final answer can be captured into `final-answer.txt`
- the raw hook trace includes enough detail to judge reads, commands, ordering, and isolation

## Practical meaning

The repo and skill are now aligned with a Codex-judged evaluator flow.
Codex CLI is a usable execution path today when local session persistence works normally.
Kiro support now depends mainly on reliable hook-trace capture, not on contract mismatch.
