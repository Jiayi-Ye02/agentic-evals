# Current Status

`skill-eval` has been migrated at the contract level to OpenClaw-native terminology and evidence flow,
and Codex CLI support for fresh child-session execution has been validated locally.

## What is ready

- repo contract updated to use OpenClaw session history as the evidence source
- artifact names normalized to `accepted-session.json`
- OpenClaw runner design documented
- helper scaffold script added for deterministic run-directory initialization
- Codex CLI smoke-tested successfully on `codex-cli 0.118.0` with a real parent session, one child session, and a persisted `thread_spawn_edges` link in `~/.codex/state_5.sqlite`

## What still depends on runtime support

A fully automated dynamic evaluation on Codex CLI still requires a live runtime where:

- `spawn_agent` can create fresh subagents successfully
- `~/.codex/sessions` and `~/.codex/state_5.sqlite` are writable and readable
- authentication and network allow live Codex sessions to complete normally

OpenClaw execution still requires a live runtime where:

- `sessions_spawn` can create fresh subagents successfully
- `sessions_history` returns enough detail to judge reads, commands, ordering, and final answers
- long-running child execution can be awaited cleanly with `sessions_yield`

## Practical meaning

The repo and skill are now aligned with the intended evaluator semantics.
Codex CLI is a usable execution path today when local session persistence works normally.
The remaining work is mostly runtime execution reliability, not repo-contract mismatch.
