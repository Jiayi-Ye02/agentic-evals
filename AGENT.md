# Agent Contract For `agentic-evals`

This file is the agent-facing contract for evaluator agents such as `skill-eval`.

Human readers should start with [README.md](./README.md). First-time operators should start with [docs/quickstart.md](./docs/quickstart.md).

## Purpose

`agentic-evals` is a target-driven evaluation repo for testing one skill at a time.

This repo is the source of truth for:

- targets
- suites
- cases
- assertions
- required run artifacts
- report shape

The target skill remains the source of truth for the behavior being tested.
The evaluator must not invent new rules when this repo is silent.

If a case cannot be judged reliably from the available evidence, mark it `blocked`.

The current default target is `voice-ai-integration`.

## Run Workflow

Every evaluator that uses this repo should follow this order:

1. Read this file.
2. Resolve `target_id`. If none is provided, use the repo default target.
3. Read `targets/<target_id>/target.yaml`.
4. Read the selected suite files.
5. Read each case file referenced by those suites, or the selected case file.
6. Create `runs/<run_id>/manifest.json`.
7. Create a parent temp directory for isolated per-case workspaces.
8. Execute each case in its own fresh isolated workspace.
9. Save a readable `transcript.md`.
10. Write one `case-results/<case_id>.json` file per case.
11. Write `report.md`.

Do not start execution before the case set is known.

## Repo Layout

```text
agentic-evals/
├── AGENT.md
├── README.md
├── docs/
│   └── quickstart.md
├── targets/
│   └── <target_id>/
│       ├── target.yaml
│       ├── suites/
│       └── cases/
└── runs/
```

## Source Of Truth

- `targets/<target_id>/target.yaml` defines the target under test, the entry skill, the skill roots that may be consulted, the default suites, the required run artifacts, and the allowed statuses.
- `targets/<target_id>/suites/` groups active cases into runnable suites.
- `targets/<target_id>/cases/` holds active cases.
- `targets/<target_id>/deferred-cases/` holds backlog cases that are intentionally not active.

Deferred cases are not part of the runnable active suite set unless a human explicitly promotes them.

## Required Run Artifacts

Each run must create:

```text
runs/<run_id>/
├── manifest.json
├── transcript.md
├── case-results/
│   ├── <case_id>.json
│   └── ...
└── report.md
```

`manifest.json` must record:

- `run_id`
- `target_id`
- `suite_ids`
- `target_skill_path`
- `started_at`
- `model` if available
- `workspace_mode` with value `isolated-per-case`
- `case_workspace_root` for the parent temp directory used for per-case workspaces
- `notes` if the environment is unusual

Each case result must record that case's accepted `workspace_root`.

## Case Status

- `pass`: all required assertions passed with enough evidence
- `fail`: one or more required assertions failed
- `blocked`: the evaluator could not judge reliably because of environment limits, unclear target behavior, or missing evidence

When a case is `blocked`, include `blocked_reason` with one of:

- `environment`
- `unclear-rule`
- `insufficient-evidence`

Only use statuses allowed by `targets/<target_id>/target.yaml`.

## Evidence Standard

Preferred evidence:

- files read
- commands executed
- ordered file and command traces
- concrete assistant outputs quoted in `transcript.md`

Do not mark a case `pass` from a generic assistant claim such as "I checked the skill" unless the transcript or tool trace shows what was actually read or run.

## Workspace Isolation

Each case must run in its own fresh isolated workspace.

Rules:

- Do not execute cases directly in the user's main workspace.
- Create a new case workspace under `case_workspace_root` for every case.
- Apply case `setup` mutations only inside that case workspace.
- No case may observe filesystem mutations left by a previous case unless the current case setup explicitly recreates them.
- Preserve the accepted case workspace at least until `case-results/<case_id>.json` and `report.md` are written. Cleanup after reporting is optional.

## Assertion Contract

Cases may include:

- optional `assert.summary` as a short human-readable description of the protected behavior
- optional per-assertion `description` to explain the intent of that single check
- optional per-assertion `evidence_scope` to hint whether the evaluator should rely mainly on `trace`, `final_answer`, or both

These human-readable fields are the assertion contract.
Older file-read, command, ordering, and route requirements should be rewritten into this natural-language form rather than kept as separate machine-oriented types.

### Assertion Entry

Use this shape for every required or forbidden assertion.

Fields:

- optional `description`
- `pass_criteria`
- optional `fail_signals`
- optional `evidence_scope`

The evaluator must judge the check from the accepted trace and final answer.
Pass only when the available evidence satisfies the pass criteria and does not show any fail signal.
If the transcript does not support a reliable answer, mark the assertion `blocked`.

## Case Result Shape

Each `case-results/<case_id>.json` file must contain:

```json
{
  "case_id": "example-case",
  "workspace_root": "/tmp/skill-eval/run-123/example-case",
  "status": "pass",
  "blocked_reason": null,
  "assertions": [
    {
      "summary": "Consulted the top-level skill instructions before answering.",
      "status": "pass",
      "evidence": ["transcript.md#L12"]
    }
  ],
  "notes": ["Short explanation."],
  "suggested_fix_files": [".agents/skills/<target_id>/SKILL.md"]
}
```

## Report Shape

`report.md` must contain exactly these sections:

1. `Run Summary`
2. `Case Table`
3. `Failures`
4. `Suggested Next Fixes`

Keep `Suggested Next Fixes` to at most 3 items and point to real files.
