# agentic-evals

`agentic-evals` is a test repo for running agentic evaluations against `voice-ai-integration`.

The repo defines:

- the evaluation protocol
- the target under test
- the available suites and cases
- the required run artifacts

## Layout

```text
agentic-evals/
├── README.md
├── docs/
│   └── test-protocol.md
├── targets/
│   └── voice-ai-integration/
│       ├── target.yaml
│       ├── suites/
│       └── cases/
└── runs/
```

## Protocol

The evaluation contract lives in `docs/test-protocol.md`.

It defines:

- the source of truth for evaluation
- the required run workflow
- the allowed case statuses
- the supported assertion types
- the required shape for `case-results/<case_id>.json`
- the required sections in `report.md`

## Target

The current target is `voice-ai-integration`.

`targets/voice-ai-integration/target.yaml` defines:

- the entry skill file
- the skill roots that may be consulted during evaluation
- the default suites
- the required run artifacts
- the allowed statuses
- the focus areas for this target

Current focus areas:

- `bootstrap`
- `intake-routing`
- `source-order`

## Suites

The target currently includes 3 suites:

- `smoke`: bootstrap checks
- `routing`: intake and product routing checks
- `source-order`: reference ordering checks

Suite files live under:

```text
targets/voice-ai-integration/suites/
```

## Cases

The target currently includes these cases:

- `bootstrap-read-skill`
- `bootstrap-missing-docs-index`
- `bootstrap-failed-no-fake-success`
- `intake-minimum-info`
- `route-convoai`
- `route-rtc`
- `source-order-local-first`
- `convoai-sample-first`

Case files live under:

```text
targets/voice-ai-integration/cases/
```

Each case includes:

- `case_id`
- `title`
- `input`
- `setup`
- `assert.required`
- `assert.forbidden`
- `notes`

## Assertions

The protocol currently supports these assertion types:

- `file_read`
- `command_executed`
- `source_order`
- `route`
- `reviewer_check`

Assertion semantics are defined in `docs/test-protocol.md`.

## Run Artifacts

Each run is stored under:

```text
runs/<run_id>/
```

A run must include:

```text
runs/<run_id>/
├── manifest.json
├── transcript.md
├── case-results/
│   ├── <case_id>.json
│   └── ...
└── report.md
```

Status values used by this repo:

- `pass`
- `fail`
- `blocked`

## Existing Run

The repo currently contains one executed run:

```text
runs/20260327T080911Z_bootstrap-missing-docs-index/
```

This run includes:

- `manifest.json`
- `transcript.md`
- `case-results/bootstrap-missing-docs-index.json`
- `report.md`

## How To Use This Repo

1. Read `docs/test-protocol.md`.
2. Read `targets/voice-ai-integration/target.yaml`.
3. Select one or more suite files, or a single case file.
4. Execute the selected cases against `voice-ai-integration`.
5. Write the required run artifacts under `runs/<run_id>/`.

## Paths

Important paths in this repo:

- `docs/test-protocol.md`
- `targets/voice-ai-integration/target.yaml`
- `targets/voice-ai-integration/suites/`
- `targets/voice-ai-integration/cases/`
- `runs/`
