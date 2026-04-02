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
│       ├── cases/
│       └── deferred-cases/
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
- `convoai-intake`
- `convoai-api`

## Suites

The target currently includes 5 suites:

- `smoke`: bootstrap checks
- `routing`: intake and product routing checks
- `source-order`: reference ordering checks
- `convoai-intake`: checklist-driven ConvoAI intake and repair behavior
- `convoai-api`: ConvoAI auth, payload, and request semantics

Suite files live under:

```text
targets/voice-ai-integration/suites/
```

## Cases

The active target currently includes 7 cases:

- `smoke` (2): `bootstrap-missing-docs-index`, `bootstrap-failed-no-fake-success`
- `routing` (2): `route-convoai`, `route-rtc`
- `source-order` (1): `convoai-sample-first`
- `convoai-intake` (1): `convoai-consolidated-checklist`
- `convoai-api` (1): `auth-prefers-rtc-token`

Active case files live under:

```text
targets/voice-ai-integration/cases/
```

Deferred cases that are useful for later regression expansion live under:

```text
targets/voice-ai-integration/deferred-cases/
```

Each case includes:

- `case_id`
- `title`
- `input`
- `setup`
- optional `assert.summary`
- `assert.required`
- `assert.forbidden`
- `notes`

## Assertions

Cases now use human-readable assertion entries only.

For maintainability:

- Prefer `assert.summary` for a short case-level description of the protected behavior.
- Express every requirement as an assertion entry with clear `description`, `pass_criteria`, and `fail_signals`.
- Preserve the old assertion meaning when converting a case. If an older case checked file reads, commands, ordering, or routing, rewrite those requirements into natural-language rubric checks instead of dropping them.
- Use `evidence_scope` to hint whether the evaluator should look mainly at `trace`, `final_answer`, or both.

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

Each run must also use isolated per-case workspaces under a temp parent directory.
Those case workspaces do not need to live inside `runs/<run_id>/`, but the run
artifacts must record the parent `case_workspace_root` and each case result must
record that case's `workspace_root`.

Status values used by this repo:

- `pass`
- `fail`
- `blocked`

## How To Use This Repo

1. Read `docs/test-protocol.md`.
2. Read `targets/voice-ai-integration/target.yaml`.
3. Select one or more suite files, or a single case file.
4. Create a parent temp directory for isolated per-case workspaces.
5. Execute the selected cases against `voice-ai-integration`, one fresh case workspace per case.
6. Write the required run artifacts under `runs/<run_id>/`.

## How To Add A Test

Use this process when adding a new case:

1. Identify one specific behavior that is worth locking down. Keep each case focused on a single routing, source-order, bootstrap, or response-quality rule.
2. Choose the smallest existing suite that matches the behavior. Create a new suite only when the new cases form a stable theme.
3. Add a new YAML file under `targets/voice-ai-integration/cases/`. Prefer a filename that matches `case_id`.
4. Keep `input.user_prompt` realistic and keep `setup` minimal. Only add setup flags that are needed to express the scenario.
5. Write every assertion as a natural-language assertion entry. If an older test idea depends on file reads, commands, ordering, or routing, convert that requirement into natural language instead of encoding it as a separate assertion type.
6. Add the new case path to one suite file under `targets/voice-ai-integration/suites/`.
7. If you created a new suite that should run by default, also add its `suite_id` to `targets/voice-ai-integration/target.yaml`.
8. Keep only the active cases under `targets/voice-ai-integration/cases/`. Move low-priority or temporarily disabled cases to `targets/voice-ai-integration/deferred-cases/` so the active suite set stays small and intentional.
9. Validate the repo after the change: all active YAML should parse, every active case should be referenced by a suite, and no suite should reference a missing case.
10. If the case relies on setup state, make sure that setup can be reproduced inside an isolated per-case workspace without mutating the user's main workspace.

Minimal case skeleton:

```yaml
case_id: "example-case"
title: "Short behavior-oriented title"

input:
  user_prompt: "Realistic user request"
  locale: "en-US"

setup:
  docs_index_present: true
  network_mode: "restricted"

assert:
  summary: "The assistant should consult the skill and then follow the supported path."
  required:
    - description: "The accepted trace should show that the top-level skill instructions were consulted before answering."
      pass_criteria:
        - "TRACE_FILES_READ includes `.agents/skills/voice-ai-integration/SKILL.md`"
      fail_signals:
        - "The accepted trace never shows a read of `.agents/skills/voice-ai-integration/SKILL.md`"
      evidence_scope:
        - "trace"
    - description: "The answer should stay on the supported implementation path."
      pass_criteria:
        - "Uses the supported path as the default recommendation"
        - "Keeps unsupported alternatives as fallback or explicitly unsupported"
      fail_signals:
        - "Leads with an unsupported path"
        - "Never distinguishes the supported path from the fallback"
      evidence_scope:
        - "final_answer"
        - "trace"

  forbidden: []

notes:
  why_it_matters: "Why this behavior is worth protecting."
  likely_fix_files:
    - ".agents/skills/voice-ai-integration/SKILL.md"
```

Useful validation commands:

```bash
ruby -e 'require "yaml"; Dir["targets/voice-ai-integration/cases/*.yaml"].sort.each { |f| YAML.load_file(f) }; Dir["targets/voice-ai-integration/suites/*.yaml"].sort.each { |f| YAML.load_file(f) }; YAML.load_file("targets/voice-ai-integration/target.yaml"); puts "yaml-ok"'
```

```bash
ruby -e 'require "yaml"; refs = Dir["targets/voice-ai-integration/suites/*.yaml"].sort.flat_map { |f| YAML.load_file(f)["cases"] }; counts = Hash.new(0); refs.each { |r| counts[r] += 1 }; cases = Dir["targets/voice-ai-integration/cases/*.yaml"].sort; missing = cases.reject { |c| counts.key?(c) }; dupes = counts.select { |_, v| v > 1 }; puts "cases=#{cases.size} suite_refs=#{refs.size} dupes=#{dupes.size} missing=#{missing.size}"'
```

## Long-Term Maintenance

Use these rules to keep the test set healthy over time:

- Keep cases behavior-first. If two cases fail for the same underlying reason, merge or rewrite them so each one protects a distinct rule.
- Keep suites thematic and readable. A suite should answer one question, such as bootstrap, routing, source ordering, intake repair, or API semantics.
- Prefer trace-based evidence over vague review. Even though every assertion is now a natural-language rubric entry, the strongest checks still point at concrete evidence such as trace reads, command attempts, ordering, and explicit route commitments.
- Preserve workspace isolation. Cases should not assume state leaked from earlier cases in the same run.
- Refresh high-value cases when the skill workflow changes. The first places to review are `targets/voice-ai-integration/target.yaml`, the affected suite file, and any case whose `likely_fix_files` point at the changed skill docs.
- Audit coverage regularly. At a minimum, check for YAML parse errors, unreferenced cases, duplicated suite entries, and stale suite descriptions whenever cases are added or removed.
- Preserve naming consistency. Use kebab-case for filenames and `case_id`, and write titles as short descriptions of the protected behavior.
- Treat external scenario lists as input, not source-of-truth. When importing candidate cases from a broader backlog, convert them into this repo's schema and assertion model instead of copying them verbatim.
- Remove or rewrite cases that no longer reflect the supported product path. A stale case is worse than no case because it creates noisy failures and hides real regressions.

## Paths

Important paths in this repo:

- `docs/test-protocol.md`
- `targets/voice-ai-integration/target.yaml`
- `targets/voice-ai-integration/suites/`
- `targets/voice-ai-integration/cases/`
- `targets/voice-ai-integration/deferred-cases/`
- `runs/`
