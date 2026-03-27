---
name: skill-eval
description: |
  Run the agentic evaluation repo for voice-ai-integration. Use when asked
  to execute repo-defined suites, collect evidence, write per-case results, and
  produce a short audit report for the target skill.
---

# Skill Eval

Use this skill only for the evaluator flow.

This skill does not define test truth.
The test repo defines the cases, assertions, and report contract.

## Required Inputs

- path to the test repo
- selected suite names, or permission to use the defaults
- path or revision of the target skill if the user provided one

Default test repo:

- folder name: `agentic-evals`
- clone URL: `https://github.com/Jiayi-Ye02/agentic-evals.git`

## Non-Negotiables

- Before any test evaluation, check whether a local `agentic-evals` folder already exists.
- If the test repo folder does not exist, clone `https://github.com/Jiayi-Ye02/agentic-evals.git` before doing anything else.
- Read `agentic-evals/docs/test-protocol.md` before running any case.
- Read `agentic-evals/targets/voice-ai-integration/target.yaml` before selecting cases.
- Read the selected suite files before executing cases.
- Do not invent pass or fail rules outside the repo.
- Do not mark `pass` from a generic self-report alone.
- If a case cannot be judged reliably, mark it `blocked`.
- On clone failure, report the error and stop. Do not silently continue without the test repo.

## Workflow

### Step 1: Acquire the test repo

Resolve the test repo path in this order:

1. If the user provided a repo path, use it.
2. Otherwise, look for a local folder named `agentic-evals` in the current workspace.
3. If that folder does not exist, run:

```bash
git clone --depth 1 https://github.com/Jiayi-Ye02/agentic-evals.git
```

Do not continue until the repo is present locally or the clone has failed.

### Step 2: Load the repo contract

Read:

- `agentic-evals/docs/test-protocol.md`
- `agentic-evals/targets/voice-ai-integration/target.yaml`
- each selected suite file
- each case file referenced by those suites

Do not start execution before the case set is known.

### Step 3: Create a run directory

Create:

```text
runs/<run_id>/
├── manifest.json
├── transcript.md
├── case-results/
└── report.md
```

`manifest.json` should include:

- `run_id`
- `target_id`
- `suite_ids`
- `target_skill_path`
- `started_at`

### Step 4: Execute each case

For every case:

1. Apply the case setup.
2. Run the target-skill evaluation flow.
3. Append concrete evidence to `transcript.md`.
4. Judge each assertion.
5. Write `case-results/<case_id>.json`.

Each case result must include:

- `case_id`
- `status`
- `blocked_reason`
- `assertions`
- `notes`
- `suggested_fix_files`

### Step 5: Write the report

`report.md` must contain exactly:

1. `Run Summary`
2. `Case Table`
3. `Failures`
4. `Suggested Next Fixes`

Keep `Suggested Next Fixes` to at most 3 items and point to real files.

## Evidence Rules

Prefer:

- file reads
- commands executed
- ordering between reads and commands
- specific assistant outputs

Use `reviewer_check` only when a behavior cannot be judged reliably from the raw trace alone.

If the trace does not support a reliable judgment, mark that assertion `blocked` and propagate the case to `blocked` unless a required assertion already failed.
