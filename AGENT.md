# Agent Contract For `agentic-evals`

This file is the agent-facing contract for evaluator agents such as `skill-eval`.

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

## Run Modes

This repo supports two evaluator run modes:

- `single-run`: the existing mode that evaluates one checked-out target skill version.
- `ab-urls`: compares two target skill versions provided as GitHub HTTP URLs.

`single-run` remains the default contract unless a caller explicitly selects `ab-urls`.

`ab-urls` compares two variants of the same `target_id`.
It does not change case truth, assertion semantics, or case status semantics.
It only adds a parent comparison run that contains two normal variant runs plus a comparison report.

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
9. Locate the accepted fresh-agent child session for each case.
10. Save the accepted child session for each case.
11. Render a readable `transcript.md` from the accepted child sessions.
12. Write one `case-results/<case_id>.json` file per case.
13. Write `report.md`.

Do not start execution before the case set is known.

For `ab-urls`:

1. Read this file.
2. Resolve `target_id`.
3. Read `targets/<target_id>/target.yaml`.
4. Read the selected suite files.
5. Read each case file referenced by those suites, or the selected case file.
6. Create `runs/<ab_run_id>/manifest.json`.
7. Resolve `variant_a_url` and `variant_b_url`.
8. Prepare one isolated source workspace per variant, each containing the local `agentic-evals/` repo plus the variant-specific target skill.
9. Create `variants/A/run/` and `variants/B/run/` under the parent run.
10. Execute a normal `single-run` flow for variant A.
11. Execute a normal `single-run` flow for variant B.
12. Compare `case-results/<case_id>.json` across A and B by `case_id`.
13. Write `comparison.json` and the parent comparison `report.md`.

The two variant runs must use the same selected case set.
Do not compare different targets, different suite selections, or differently filtered case sets inside one `ab-urls` run.

## Repo Layout

```text
agentic-evals/
├── AGENT.md
├── README.md
├── docs/
│   └── session-evidence.md
├── scripts/
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
- `docs/session-evidence.md` defines the local session evidence model.

Deferred cases are not part of the runnable active suite set unless a human explicitly promotes them.

## Required Run Artifacts

### `single-run`

Each run must create:

```text
runs/<run_id>/
├── manifest.json
├── case-artifacts/
│   ├── <case_id>/
│   │   ├── accepted-session.jsonl
│   │   └── final-answer.txt
│   └── ...
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
- `evidence_mode` with value `codex-local-session-store`
- `notes` if the environment is unusual

Each case result must record that case's accepted `workspace_root`.

### `ab-urls`

Each A/B parent run must create:

```text
runs/<ab_run_id>/
├── manifest.json
├── variants/
│   ├── A/
│   │   ├── source-manifest.json
│   │   └── run/
│   │       ├── manifest.json
│   │       ├── case-artifacts/
│   │       ├── transcript.md
│   │       ├── case-results/
│   │       └── report.md
│   └── B/
│       ├── source-manifest.json
│       └── run/
│           ├── manifest.json
│           ├── case-artifacts/
│           ├── transcript.md
│           ├── case-results/
│           └── report.md
├── comparison.json
└── report.md
```

Parent `manifest.json` must record:

- `run_mode` with value `ab-urls`
- `run_id`
- `target_id`
- `suite_ids`
- `selected_case_ids`
- `started_at`
- `variant_source_root`
- `variants.<label>.source_url`
- `variants.<label>.variant_run_dir`
- `notes`

Each variant run under `variants/<label>/run/` must satisfy the full `single-run` artifact contract.

Each `source-manifest.json` must record:

- the original GitHub HTTP URL
- the normalized GitHub URL interpretation
- the resolved repo URL
- the resolved ref
- the resolved skill subdir
- the local checkout path
- the prepared source workspace path

## Case Status

- `pass`: all required assertions passed with enough evidence
- `fail`: one or more required assertions failed
- `blocked`: the evaluator could not judge reliably because of environment limits, unclear target behavior, or missing evidence

When a case is `blocked`, include `blocked_reason` with one of:

- `environment`
- `unclear-rule`
- `insufficient-evidence`

Only use statuses allowed by `targets/<target_id>/target.yaml`.

## Evidence Policy

Preferred evidence:

- the accepted fresh-agent child session JSONL from the local Codex session store
- the accepted final answer extracted from that child session
- local thread linkage from `state_5.sqlite` only to find and disambiguate the child session

The accepted child session JSONL is the authoritative local evidence source for the current framework.
`transcript.md` is a derived human-readable view of that accepted session evidence.
Do not mark a case `pass` from a generic assistant claim such as "I checked the skill" unless the accepted session evidence shows what was actually read or run.

Static reads by the evaluator are allowed for:

- loading the repo contract
- understanding a case
- understanding the target skill after the fresh-agent run
- mapping failures to likely fix files

Static reads by the evaluator are not enough on their own to mark a dynamic case `pass` when a fresh-agent run was available.

If the local session store is unavailable, if the accepted child session cannot be located, or if the session evidence is too coarse to support the assertion, do not judge the case as `pass`.
Mark the case `blocked` with:

- `environment` when the local evidence source is unavailable
- `insufficient-evidence` when the session exists but cannot support a reliable judgment

Invalid attempts can explain `notes`, but they cannot satisfy assertions or justify a `pass`.

## Workspace Isolation

Each case must run in its own fresh isolated workspace.

Rules:

- Do not execute cases directly in the user's main workspace.
- Create a new case workspace under `case_workspace_root` for every case.
- Apply case `setup` mutations only inside that case workspace.
- No case may observe filesystem mutations left by a previous case unless the current case setup explicitly recreates them.
- Preserve the accepted case workspace at least until `case-results/<case_id>.json` and `report.md` are written. Cleanup after reporting is optional.
- Judge isolation from observed session evidence, not from fresh-agent self-reporting.
- For Codex `spawn_agent` evidence, treat per-tool `workdir` values, resolved read/write paths, and command-derived cwd outputs as authoritative isolation signals.
- Do not treat child `session_meta.cwd` as authoritative isolation evidence by itself, because spawned child-thread metadata may inherit the parent workspace cwd.
- Treat any observed access outside the case workspace as invalid evidence for that attempt.
- If no reliable per-tool workdir, resolved path, or command-derived cwd can be observed, that evidence cannot justify a `pass`.

## Assertion Contract

Cases may include:

- optional `assert.summary` as a short human-readable description of the protected behavior
- optional per-assertion `description` to explain the intent of that single check
- optional per-assertion `evidence_scope` to hint which accepted artifact file the evaluator should rely on, such as `accepted-session.jsonl` or `final-answer.txt`

These human-readable fields are the assertion contract.
Older requirements should be written in terms of consultation, observed commands, ordering, and final answers, not idealized runtime-native events.

### Assertion Entry

Use this shape for every required or forbidden assertion.

Fields:

- optional `description`
- `pass_criteria`
- optional `fail_signals`
- optional `evidence_scope`

The evaluator must judge the check from the accepted session evidence and the accepted final answer.
Pass only when the available evidence satisfies the pass criteria and does not show any fail signal.
If the accepted session evidence does not support a reliable answer, mark the assertion `blocked`.

## Case Result Shape

Each `case-results/<case_id>.json` file must contain:

```json
{
  "case_id": "example-case",
  "workspace_root": "/tmp/skill-eval/run-123/example-case",
  "thread_id": "019d41f7-25c8-7023-875d-e092d2c253ed",
  "session_path": "/Users/name/.codex/sessions/...jsonl",
  "status": "pass",
  "blocked_reason": null,
  "assertions": [
    {
      "summary": "Consulted the top-level skill instructions before answering.",
      "status": "pass",
      "evidence": [
        "case-artifacts/example-case/accepted-session.jsonl#L12"
      ]
    }
  ],
  "notes": ["Short explanation."],
  "suggested_fix_files": [".agents/skills/<target_id>/SKILL.md"]
}
```

Prefer `accepted-session.jsonl#L<line>` references in `evidence`.
Use `transcript.md#L<line>` only as a readability aid.

## Report Shape

`report.md` must contain exactly these sections:

1. `Run Summary`
2. `Case Table`
3. `Failures`
4. `Suggested Next Fixes`

Keep `Suggested Next Fixes` to at most 3 items and point to real files.

## A/B Comparison Contract

`ab-urls` parent runs compare A and B by `case_id`.

The comparison is not a new source of truth.
It is a derived summary over the two variant runs.

### Accepted Comparison Labels

Parent `comparison.json` may classify each case as:

- `same-pass`
- `same-fail`
- `same-blocked`
- `regression`
- `improvement`
- `behavior-change`
- `environment-divergence`

Suggested interpretation:

- `regression`: A was `pass`, B became `fail` or `blocked`
- `improvement`: A was `fail` or `blocked`, B became `pass`
- `behavior-change`: both variants produced results, but status or assertion outcomes changed without a clear pass-only improvement/regression shape
- `environment-divergence`: one side did not produce a comparable case result or the difference is dominated by environment/runtime failure

### A/B Parent Report Shape

Parent `report.md` for `ab-urls` must contain exactly these sections:

1. `Comparison Summary`
2. `Variant Table`
3. `Case Matrix`
4. `Regressions`
5. `Improvements`
6. `Suggested Next Fixes`

Keep `Suggested Next Fixes` to at most 3 items and prefer real target-skill files referenced by regressing or behavior-changing cases.
