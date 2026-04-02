# agentic-evals

`agentic-evals` is a target-driven evaluation repo for testing one skill at a time.


This repo defines:

- the evaluator contract in `AGENT.md`
- the target under test in `targets/<target_id>/target.yaml`
- the active suites and cases under `targets/<target_id>/`
- the run artifacts written to `runs/<run_id>/`

## Layout

```text
agentic-evals/
├── AGENT.md
├── README.md
├── targets/
│   └── <target_id>/
│       ├── target.yaml
│       ├── suites/
│       └── cases/
└── runs/
```

## Document Responsibilities

- `README.md`: human-facing repo guide for understanding and editing the test set.
- `AGENT.md`: canonical evaluator-facing repo contract.
- `.agents/skills/skill-eval/SKILL.md`: operational instructions for the `skill-eval` evaluator skill, not the source of truth for repo assertions or statuses.

## How To Read This Repo

- Read `AGENT.md` if you are changing evaluator behavior or validating repo contract rules.
- Read `targets/<target_id>/target.yaml`, suite files, and case files when editing the test set.
- Inspect `runs/` when reviewing actual execution output.

Examples in this README use `voice-ai-integration` as the target id.

## What Usually Changes

Most manual edits in this repo land in one of these places:

- `targets/<target_id>/target.yaml` when the default suites, entry skill, or allowed statuses change
- `targets/<target_id>/suites/*.yaml` when grouping active cases
- `targets/<target_id>/cases/*.yaml` when adding or refining active behavior checks

The evaluator execution protocol lives in `AGENT.md`, not here.

## Case Authoring

Add active cases under `targets/<target_id>/cases/` and reference each one from exactly one suite in `targets/<target_id>/suites/`.

Keep cases focused and behavior-first:

- Lock down one specific rule per case.
- Keep `input.user_prompt` realistic and `setup` minimal.
- Write assertions as natural-language rubric entries.
- Use `assert.summary` for the case-level behavior being protected.
- Use `evidence_scope` to point the evaluator to `trace`, `final_answer`, or both.
- Make sure any setup can be reproduced inside an isolated case workspace.

Each case should include:

- `case_id`
- `title`
- `input`
- `setup`
- optional `assert.summary`
- `assert.required`
- `assert.forbidden`
- `notes`

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
        - "TRACE_FILES_READ includes `.agents/skills/<target_id>/SKILL.md`"
      fail_signals:
        - "The accepted trace never shows a read of `.agents/skills/<target_id>/SKILL.md`"
      evidence_scope:
        - "trace"
  forbidden: []

notes:
  why_it_matters: "Why this behavior is worth protecting."
  likely_fix_files:
    - ".agents/skills/<target_id>/SKILL.md"
```

## Validation

- This command validates all case, suite, and target YAML files for the selected target by loading them with Ruby. If every file parses successfully, it prints `yaml-ok`.

```bash
TARGET_ID=voice-ai-integration ruby -e 'require "yaml"; Dir["targets/#{ENV.fetch("TARGET_ID")}/cases/*.yaml"].sort.each { |f| YAML.load_file(f) }; Dir["targets/#{ENV.fetch("TARGET_ID")}/suites/*.yaml"].sort.each { |f| YAML.load_file(f) }; YAML.load_file("targets/#{ENV.fetch("TARGET_ID")}/target.yaml"); puts "yaml-ok"'
```

- This command checks suite-to-case coverage for the selected target. It reports how many case files exist, how many suite references were found, and whether any cases are missing or referenced more than once.

```bash
TARGET_ID=voice-ai-integration ruby -e 'require "yaml"; target_id = ENV.fetch("TARGET_ID"); refs = Dir["targets/#{target_id}/suites/*.yaml"].sort.flat_map { |f| YAML.load_file(f)["cases"] }; counts = Hash.new(0); refs.each { |r| counts[r] += 1 }; cases = Dir["targets/#{target_id}/cases/*.yaml"].sort; missing = cases.reject { |c| counts.key?(c) }; dupes = counts.select { |_, v| v > 1 }; puts "cases=#{cases.size} suite_refs=#{refs.size} dupes=#{dupes.size} missing=#{missing.size}"'
```

## Maintenance

- Keep suites thematic and readable.
- Prefer concrete trace evidence over vague review criteria.
- Audit for YAML parse errors, duplicate suite references, and unreferenced cases whenever the test set changes.
- Refresh affected suites and cases when the target workflow changes.
- Remove or rewrite stale cases that no longer reflect the supported path.

## Key Paths

- `.agents/skills/skill-eval/SKILL.md`
- `AGENT.md`
- `targets/<target_id>/target.yaml`
- `targets/<target_id>/suites/`
- `targets/<target_id>/cases/`
- `runs/`
