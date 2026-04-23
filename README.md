# agentic-evals

`agentic-evals` is a target-driven evaluation repo for testing one skill at a time.

This repo defines:

- the evaluator contract in `AGENT.md`
- the target under test in `targets/<target_id>/target.yaml`
- the active suites and cases under `targets/<target_id>/`
- the run artifacts written to `runs/<run_id>/`

The repo contract is runtime-neutral: evaluators may execute it in Codex, OpenClaw, or Kiro as long as they honor the artifact contract and record the chosen runtime in `manifest.json.evidence_mode`.

## Run Modes

The repo supports 2 evaluator-facing run modes:

- `single-run`: evaluate one local target-skill workspace
- `ab-urls`: evaluate 2 isolated target-skill variants prepared from GitHub URLs, then compare them

`ab-urls` is additive.
It does not change the meaning of targets, suites, cases, assertions, or per-case statuses.

## Layout

```text
agentic-evals/
├── AGENT.md
├── README.md
├── docs/
│   └── session-evidence.md
├── targets/
│   └── <target_id>/
│       ├── target.yaml
│       └── cases/
│           └── <suite_id>/
│               ├── suite.yaml
│               └── <case_id>.yaml
└── runs/
```

## Document Responsibilities

- `README.md`: human-facing repo guide for understanding and editing the test set.
- `AGENT.md`: canonical evaluator-facing repo contract.
- `docs/session-evidence.md`: canonical contract for runtime-native evidence and accepted-session location.
- `skill-eval/SKILL.md`: operational instructions for the `skill-eval` evaluator skill, not the source of truth for repo assertions or statuses.

## How To Read This Repo

- Read `AGENT.md` if you are changing evaluator behavior or validating repo contract rules.
- Read `targets/<target_id>/target.yaml`, suite files, and case files when editing the test set.
- Inspect `runs/` when reviewing actual execution output.

Examples in this README use `voice-ai-integration` as the target id.

## A/B Usage

Recommended first-version URL shape:

- `https://github.com/<org>/<repo>/tree/<ref>/<subdir>`

This is preferred because it encodes both the git ref and the exact skill root.

Supported URL families for variant acquisition:

- `https://github.com/<org>/<repo>/tree/<ref>/<subdir>`
- `https://github.com/<org>/<repo>/archive/refs/heads/<branch>.tar.gz`
- `https://github.com/<org>/<repo>/archive/refs/tags/<tag>.tar.gz`
- `https://github.com/<org>/<repo>/archive/<commit>.tar.gz`

Example A/B prompts:

```text
用 skill-eval 以 ab 模式测试 target_id=voice-ai-integration
variant_a_url=https://github.com/org/repo/tree/main/.agents/skills/voice-ai-integration
variant_b_url=https://github.com/org/repo/tree/rewrite/.agents/skills/voice-ai-integration
suite_ids=workflow,routing
```

```text
用 skill-eval 做 A/B 测试
target_id=voice-ai-integration
A=https://github.com/org/repo/tree/main/.agents/skills/voice-ai-integration
B=https://github.com/org/repo/tree/feature-x/.agents/skills/voice-ai-integration
case_id=auth-prefers-rtc-token
```

## A/B Artifact Layout

An `ab-urls` run writes a top-level comparison wrapper plus 2 variant-local `single-run` directories:

```text
agentic-evals/runs/<ab_run_id>/
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

Meaning:

- `variants/<label>/run/` is still a normal single-version run shape
- `source-manifest.json` records how each URL was parsed and resolved
- `comparison.json` and the top-level `report.md` summarize case-by-case differences

## What Usually Changes

Most manual edits in this repo land in one of these places:

- `targets/<target_id>/target.yaml` when the default suites, entry skill, or allowed statuses change
- `targets/<target_id>/cases/<suite_id>/suite.yaml` when grouping active cases
- `targets/<target_id>/cases/<suite_id>/<case_id>.yaml` when adding or refining active behavior checks

The evaluator execution protocol lives in `AGENT.md`, not here.

## Case Authoring

Add active cases under `targets/<target_id>/cases/<suite_id>/` alongside the `suite.yaml` that references them.

Keep cases focused and behavior-first:

- Lock down one specific rule per case.
- Keep `input.user_prompt` realistic and `setup` minimal.
- Write assertions as natural-language rubric entries.
- Use `assert.summary` for the case-level behavior being protected.
- Use `evidence_scope` to point the evaluator to artifact filenames such as `accepted-session.json`, `raw-hook-trace.jsonl`, `final-answer.txt`, or any combination of them.
- Write trace-facing assertions against accepted session evidence semantics such as consultation of a file, an observed command invocation, ordering, and the final answer.
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

assert:
  summary: "The assistant should consult the skill and then follow the supported path."
  required:
    - description: "The accepted session evidence should show that the top-level skill instructions were consulted before answering."
      pass_criteria:
        - "The accepted session evidence shows consultation of `.agents/skills/<target_id>/SKILL.md` before the answer."
      fail_signals:
        - "The accepted session evidence never shows consultation of `.agents/skills/<target_id>/SKILL.md`"
      evidence_scope:
        - "accepted-session.json"
  forbidden: []

notes:
  why_it_matters: "Why this behavior is worth protecting."
  likely_fix_files:
    - ".agents/skills/<target_id>/SKILL.md"
```

## Validation

- This command validates all case, suite, and target YAML files for the selected target by loading them with Ruby. If every file parses successfully, it prints `yaml-ok`.

```bash
TARGET_ID=voice-ai-integration ruby -e 'require "yaml"; Dir["targets/#{ENV.fetch("TARGET_ID")}/cases/*/suite.yaml"].sort.each { |f| YAML.load_file(f) }; Dir["targets/#{ENV.fetch("TARGET_ID")}/cases/**/*.yaml"].sort.reject { |f| f.end_with?("suite.yaml") }.each { |f| YAML.load_file(f) }; YAML.load_file("targets/#{ENV.fetch("TARGET_ID")}/target.yaml"); puts "yaml-ok"'
```

- This command checks suite-to-case coverage for the selected target. It reports how many case files exist, how many suite references were found, and whether any cases are missing or referenced more than once.

```bash
TARGET_ID=voice-ai-integration ruby -e 'require "yaml"; target_id = ENV.fetch("TARGET_ID"); refs = Dir["targets/#{target_id}/cases/*/suite.yaml"].sort.flat_map { |f| YAML.load_file(f)["cases"] }; counts = Hash.new(0); refs.each { |r| counts[r] += 1 }; cases = Dir["targets/#{target_id}/cases/**/*.yaml"].sort.reject { |f| f.end_with?("suite.yaml") }; missing = cases.reject { |c| counts.key?(c) }; dupes = counts.select { |_, v| v > 1 }; puts "cases=#{cases.size} suite_refs=#{refs.size} dupes=#{dupes.size} missing=#{missing.size}"'
```

## Maintenance

- Keep suites thematic and readable.
- Prefer concrete session evidence over vague review criteria.
- Audit for YAML parse errors, duplicate suite references, and unreferenced cases whenever the test set changes.
- Refresh affected suites and cases when the target workflow changes.
- Remove or rewrite stale cases that no longer reflect the supported path.

## Key Paths

- `.github/workflows/skill-eval-kiro.yml`
- `scripts/capture_kiro_hook.py`
- `scripts/write_kiro_hook_agent.py`
- `scripts/normalize_kiro_hook_trace.py`
- `scripts/analyze_kiro_hook_trace.py`
- `docs/kiro-runtime-agent-prompt.txt`
- `docs/kiro-runtime-smoke-test.md`
- `skill-eval/SKILL.md`
- `AGENT.md`
- `docs/session-evidence.md`
- `targets/<target_id>/target.yaml`
- `targets/<target_id>/cases/<suite_id>/suite.yaml`
- `targets/<target_id>/cases/<suite_id>/<case_id>.yaml`
- `runs/`
