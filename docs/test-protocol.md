# Agentic Eval Protocol

This repo is a proof-of-concept evaluator for `voice-ai-integration`.

The goal is not to build a complete eval platform. The goal is to answer:

1. Can a repo-defined evaluator run the same way more than once?
2. Can it catch real problems in `voice-ai-integration`?
3. Can the output guide concrete edits to the target skill?

## Source Of Truth

- This test repo is the source of truth for suites, cases, assertions, and report shape.
- The target skill is the source of truth for the behavior being tested.
- The evaluator skill must not invent new rules when the repo is silent.

If a case cannot be judged reliably from the available evidence, mark it `blocked`.

## Run Workflow

Every run should follow this order:

1. Read this file.
2. Read `targets/voice-ai-integration/target.yaml`.
3. Read the selected suite files.
4. Create `runs/<run_id>/manifest.json`.
5. Execute each case.
6. Save a readable `transcript.md`.
7. Write one `case-results/<case_id>.json` file per case.
8. Write `report.md`.

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
- `notes` if the environment is unusual

## Case Status

- `pass`: all required assertions passed with enough evidence
- `fail`: one or more required assertions failed
- `blocked`: the evaluator could not judge reliably because of environment limits, unclear target behavior, or missing evidence

When a case is `blocked`, include `blocked_reason` with one of:

- `environment`
- `unclear-rule`
- `insufficient-evidence`

## Evidence Standard

Preferred evidence:

- files read
- commands executed
- ordered file/command traces
- concrete assistant outputs quoted in `transcript.md`

Do not mark a case `pass` from a generic assistant claim such as "I checked the skill" unless the transcript or tool trace shows what was actually read or run.

## Supported Assertion Types

### `file_read`

Pass when the transcript or tool trace shows the evaluator opened the expected file.

Fields:

- `path`
- optional `before_any_of`

### `command_executed`

Pass when the transcript or tool trace shows the command was attempted.

Fields:

- `argv_prefix`

### `source_order`

Pass when the evidence shows one source was consulted before another source.

Fields:

- `first`
- `before`

### `route`

Pass when the transcript clearly states the chosen primary route.

- `convoai-primary`
- `rtc-primary`
- `token-server-primary`

### `reviewer_check`

Use this only when the behavior cannot be made reliable from file or command traces alone.

Fields:

- `prompt`

The evaluator must answer the prompt from evidence in the transcript. If the transcript does not support a reliable answer, mark the assertion `blocked`.

## Case Result Shape

Each `case-results/<case_id>.json` file must contain:

```json
{
  "case_id": "example-case",
  "status": "pass",
  "blocked_reason": null,
  "assertions": [
    {
      "type": "file_read",
      "summary": "Read SKILL.md before any routing file",
      "status": "pass",
      "evidence": ["transcript.md#L12"]
    }
  ],
  "notes": ["Short explanation."],
  "suggested_fix_files": [".agents/skills/voice-ai-integration/SKILL.md"]
}
```

## Report Shape

`report.md` must contain exactly these sections:

1. `Run Summary`
2. `Case Table`
3. `Failures`
4. `Suggested Next Fixes`

The final section should list at most 3 concrete fixes and point to real files.
