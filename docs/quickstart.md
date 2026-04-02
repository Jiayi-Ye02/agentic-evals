# Quickstart For First-Time Users

This guide is for people who have never used an agentic test setup before.

If you only want one thing to remember, remember this:

`agentic-evals` defines what to test, `skill-eval` runs the test, and a fresh Codex sub-agent is the thing being judged.

## What This System Is

This repo does not test a normal function or CLI command.
It tests how an agent behaves when it uses a target skill.

In this setup, there are 4 different roles:

1. `agentic-evals/`
   This is the test repo. It is the source of truth for targets, suites, cases, assertions, and output format.
2. `skill-eval`
   This is the evaluator skill. It knows how to run the repo-defined protocol.
3. target skill
   This is the skill under test, for example `.agents/skills/voice-ai-integration/`.
4. fresh Codex sub-agent
   This is the execution subject. It receives the case prompt and produces the trace and answer that the evaluator judges.

That separation matters:

- the test repo decides pass or fail rules
- the evaluator runs the process
- the fresh sub-agent is what actually gets tested

## What You Need Before Your First Run

Your workspace should normally look like this:

```text
<workspace>/
├── .agents/
│   └── skills/
│       ├── skill-eval/
│       └── <target-skill>/
└── agentic-evals/
```

You also need:

- a Codex environment that can use `spawn_agent`
- the target skill files present locally
- the `agentic-evals` repo present locally, or permission for the evaluator to clone it if missing

## The 5-Minute Mental Model

When you ask Codex to run an eval, the expected flow is:

1. Codex uses `skill-eval`.
2. `skill-eval` reads the protocol in [`docs/test-protocol.md`](./test-protocol.md).
3. It resolves the target from [`targets/<target_id>/target.yaml`](../targets/voice-ai-integration/target.yaml).
4. It reads the selected suite or case files from `targets/<target_id>/`.
5. It creates a new run directory under `runs/<run_id>/`.
6. For each case, it creates a brand-new isolated temp workspace.
7. It spawns a fresh sub-agent for that case.
8. The fresh sub-agent answers the case prompt and returns:
   - files it read
   - commands it ran
   - the final user-facing answer
9. The evaluator validates isolation and judges the assertions.
10. The evaluator writes the final artifacts.

## Fastest Way To Run It

Ask Codex in plain language to use `skill-eval`.

### Examples:

Single case:

```text
Use skill-eval to test target_id=voice-ai-integration, case_id=convoai-phase1-only-before-gates.
```

Single suite:

```text
Use skill-eval to test target_id=voice-ai-integration, suite=source-order.
```

Default target with default suites:

```text
Use skill-eval to run the default target with its default suites.
```

### Chinese example:

```text
用 skill-eval 去测试 target_id=voice-ai-integration，测试范围 case_id=convoai-phase1-only-before-gates
```

You do not need to manually create `runs/` folders or temp workspaces yourself.
That is the evaluator's job.

## What To Expect During A Run

During execution, the evaluator should:

- report which target, suite, or case it is using
- create a fresh case workspace under a temp directory
- spawn a fresh sub-agent for the case
- tell you the sub-agent nickname or id so you can open it and monitor in the Codex app
- write artifacts under `runs/<run_id>/`

The evaluator should not:

- run the case directly in your main workspace
- silently replace the fresh sub-agent with a fallback executor
- mark `pass` from a vague self-report alone

## Where To Look After The Run

Every run should create:

```text
runs/<run_id>/
├── manifest.json
├── transcript.md
├── case-results/
└── report.md
```

Use these files like this:

- `report.md`: start here for the short answer
- `case-results/<case_id>.json`: the official status for one case
- `transcript.md`: the accepted trace and final answer used for judgment
- `manifest.json`: run metadata, workspace mode, and environment mismatch notes

## How To Read The Result

Status meanings:

- `pass`: the assertions were satisfied with enough evidence
- `fail`: at least one required assertion failed
- `blocked`: the evaluator could not judge reliably

`blocked` is not the same as `fail`.
It usually means the environment or evidence was not good enough to make a safe judgment.


## Common Problems

### `agentic-evals` is missing

The evaluator should first look for a local `agentic-evals/` folder.
If it does not exist, it should clone the default repo before continuing.

### `spawn_agent` is unavailable

Stop the run.
Do not substitute another execution method.

### A case got `blocked`

Open `manifest.json` and `transcript.md` first.
Most blocked cases come from:

- environment mismatch
- insufficient evidence
- invalid isolation

### A run passed but you do not trust it

Open `transcript.md` and inspect the accepted trace.
The trace should show what the fresh sub-agent actually read and ran.

## If You Want To Go Deeper

After your first successful run, these are the next files to read:

- [`docs/test-protocol.md`](./test-protocol.md)
- [`README.md`](../README.md)
- [`targets/voice-ai-integration/target.yaml`](../targets/voice-ai-integration/target.yaml)

If you want to add or edit tests, start from [`README.md`](../README.md), not from this quickstart.
