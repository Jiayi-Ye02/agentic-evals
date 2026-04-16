---
name: skill-eval
description: |
  Run the agentic evaluation repo for a target skill. Use when
  asked to execute repo-defined suites, collect evidence, write per-case
  results, and produce a short audit report for the target skill.
  Also supports evaluation modes: AB tests, subjective scoring, and
  vendor comparisons via evaluation YAML files in the eval repo.
---

# Skill Eval

Use this skill only for the evaluator flow.

This skill does not define test truth.
The eval repo defines the targets, suites, cases, assertions, evaluations, rubrics, statuses, and report contract.

This skill is a dynamic black-box evaluator.
Do not replace execution with a static read-through when a fresh-agent run is possible.

## File Responsibilities

Use the docs in this order and keep their roles separate:

- `agentic-evals/AGENT.md`: canonical repo contract for any evaluator agent. Read this first for run outputs, statuses, assertion semantics, isolation rules, evaluation modes, and report shape.
- `agentic-evals/docs/session-evidence.md`: required local evidence contract for locating runtime-native evidence and preserving it in `accepted-session.json`.
- `agentic-evals/targets/<target_id>/target.yaml`: target-specific contract, including entry skill, roots, default suites, and allowed statuses.
- `agentic-evals/targets/<target_id>/cases/<suite_id>/suite.yaml`: selected runnable suite definitions.
- `agentic-evals/targets/<target_id>/cases/<suite_id>/<case_id>.yaml`: per-case prompts, setup, and assertions.
- `agentic-evals/evaluations/<mode>/<eval_id>.yaml`: evaluation definitions for AB, comparison, or subjective modes.
- `agentic-evals/rubrics/<rubric_id>.yaml`: scoring dimensions and anchors for rubric-based evaluation.
- `.agents/skills/skills-evaluation/SKILL.md`: how this evaluator skill acquires the repo, creates isolated workspaces, spawns fresh agents, locates child sessions, validates isolation, and writes the repo-defined artifacts.

Do not duplicate repo contract rules from `AGENT.md` unless this skill needs an extra operational constraint.

## Required Inputs

- optional path to the test repo
- `target_id`, or permission to use the repo default
- selected suite names, case ids, or permission to use the defaults
- path or revision of the target skill if the user provided one
- optional run mode: `single-run` or `ab-urls`
- optional `execution_runtime`: `codex` or `kiro`
- for `ab-urls`: `variant_a_url` and `variant_b_url`, both GitHub HTTP URLs to the target skill version

If the user does not provide a test repo path, the evaluator must first look for a local
`agentic-evals` folder in the current workspace and clone the default repo only if that
folder is missing.

Default test repo:

- folder name: `agentic-evals`
- clone URL: `https://github.com/Jiayi-Ye02/agentic-evals.git`

For `ab-urls`, recommended variant URL formats are:

- `https://github.com/<org>/<repo>/tree/<ref>/<skill-dir>`
- `https://github.com/<org>/<repo>/blob/<ref>/<skill-dir>/SKILL.md`

## Runtime Support

`skill-eval` keeps Codex as the evaluator runtime.
It supports two execution runtimes:

- Codex, judged from the accepted child session stored under `~/.codex/sessions/`
- Kiro, judged from raw hook traces captured during the run and preserved in `accepted-session.json`

Codex execution support has been validated locally with `codex-cli 0.118.0` where:

- `multi_agent` is enabled
- a parent Codex session can create a child session successfully
- the child session is recorded in `~/.codex/sessions/...jsonl`
- the parent-child edge is recorded in `~/.codex/state_5.sqlite` `thread_spawn_edges`

Operational constraints for Codex execution:

- case execution still must happen through `spawn_agent` with `fork_context: false`
- do not replace case execution with `codex exec`
- `codex exec` is acceptable only as an environment smoke test for child-session creation
- `~/.codex` must be writable so the session store and state database can update normally
- authentication and network access must allow a normal live Codex session to complete

Operational constraints for Kiro execution:

- Codex remains the evaluator and judge
- the evaluator must launch Kiro inside the isolated case workspace
- Kiro hooks must append raw JSON lines to `case-artifacts/<case_id>/raw-hook-trace.jsonl`
- `accepted-session.json` must preserve the accepted raw evidence stream for the runtime under test
- if the evaluator cannot retrieve a reliable raw hook trace, stop or mark the case `blocked` instead of judging from a summary

## Non-Negotiables

- Before any test evaluation, check whether a local `agentic-evals` folder already exists.
- If the test repo folder does not exist, clone `https://github.com/Jiayi-Ye02/agentic-evals.git` before doing anything else.
- Read `agentic-evals/AGENT.md` before running any case.
- Resolve `target_id` before selecting cases. Use the user-provided `target_id` when available. Otherwise, use the repo default target.
- Read `agentic-evals/targets/<target_id>/target.yaml` before selecting cases.
- Read the selected suite files and case files before executing cases.
- Create one brand-new isolated workspace for every case attempt under a temp parent directory. Never execute a case in the user's main workspace.
- Keep Codex as the evaluator even when the execution runtime is Kiro.
- When `execution_runtime=codex`, execute each case by running a fresh Codex sub-agent on the case prompt with `spawn_agent` and `fork_context: false`.
- When `execution_runtime=kiro`, run Kiro directly from the current Codex evaluator inside the isolated case workspace. Extract the case `input.user_prompt` verbatim, configure local raw-hook capture, launch `kiro-cli chat`, capture stdout to `final-answer.txt`, copy the accepted raw hook stream into `accepted-session.json`, and keep judgment in the current Codex thread.
- When a lower-level debugging pass is needed, you may still run Kiro in the isolated case workspace with raw hook tracing enabled.
- Do not use `codex exec`, terminal wrappers, or any other fallback executor as a substitute for the selected case execution runtime.
- If `execution_runtime=codex` and `spawn_agent` is unavailable or agent creation fails, stop the evaluation immediately and report the failure reason instead of continuing.
- If `execution_runtime=codex` and the runtime cannot write normal Codex session artifacts under `~/.codex`, stop and report an environment block instead of continuing with degraded evidence.
- If `execution_runtime=kiro` and the evaluator cannot capture `raw-hook-trace.jsonl`, stop or mark the case `blocked` instead of continuing with degraded evidence.
- After each successful Codex `spawn_agent`, immediately report the sub-agent nickname in the main thread so the user can find and open it in the Codex app. If no nickname is available, report the agent id.
- Send the case `input.user_prompt` to the fresh agent verbatim. Do not paraphrase the user request.
- Do not leak the case title, assertions, expected route, intended answer, or your prior judgment into the fresh-agent prompt.
- The fresh sub-agent is the execution subject, not the judge. Do not ask it to grade the case, interpret the assertions, or decide pass or fail.
- Do not ask the fresh sub-agent to self-report `TRACE_FILES_READ`, `TRACE_COMMANDS_EXECUTED`, or any other evaluator-facing execution log.
- Judge from authoritative runtime evidence, not from fresh-agent self-reporting.
- Do not invent pass or fail rules outside the repo.
- Do not mark `pass` from a generic self-report alone.
- Do not mark `pass` from a static source review alone when a fresh-agent run was available.
- Treat any attempt that observably reads or executes outside its case workspace as invalid evidence. Do not judge the case from that attempt.
- If a case cannot be judged reliably, mark it `blocked`.
- On clone failure, report the error and stop. Do not silently continue without the test repo.
- In `ab-urls` mode, do not mutate or swap the user's local target skill tree. Prepare one isolated source workspace per variant URL.
- In `ab-urls` mode, compare only the same selected case set across A and B.

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

- `agentic-evals/AGENT.md`
- `agentic-evals/docs/session-evidence.md`
- `agentic-evals/targets/<target_id>/target.yaml`
- each selected suite file
- each case file referenced by those suites, or the selected case file

`AGENT.md` defines the repo contract.
This skill executes that contract.

### Step 3: Create the run directory

Create the run directory and files exactly as required by `agentic-evals/AGENT.md`.

At minimum, the run must contain:

```text
runs/<run_id>/
├── manifest.json
├── case-artifacts/
├── transcript.md
├── case-results/
└── report.md
```

When writing `manifest.json`, include any environment notes this skill discovers while setting up isolated workspaces or locating runtime-native evidence.

For `ab-urls`, initialize the parent run with:

```bash
python3 .agents/skills/skills-evaluation/scripts/init_ab_run.py "<source_workspace>" "<target_id>" "<variant_a_url>" "<variant_b_url>" [--suite-id <suite_id>] [--case-id <case_id>]
```

This creates:

- parent `runs/<ab_run_id>/manifest.json`
- `variants/A/run/`
- `variants/B/run/`
- optional `variants/A/source-manifest.json`
- optional `variants/B/source-manifest.json`

Each `variants/<label>/run/` directory must later satisfy the normal `single-run` artifact contract.

### Step 3A: Resolve A/B variant sources

In `ab-urls` mode:

1. Parse each GitHub URL with `.agents/skills/skills-evaluation/scripts/parse_github_skill_url.py`.
2. Prepare one isolated source workspace per variant with `.agents/skills/skills-evaluation/scripts/prepare_variant_source_workspace.py`.
3. Record the prepared source workspace and normalized URL interpretation in `variants/<label>/source-manifest.json`.

Each prepared source workspace must contain:

```text
<prepared-source>/
├── agentic-evals/
└── .agents/
    └── skills/
        └── <target_id>/
```

The local `agentic-evals/` repo stays the source of truth.
Only the target skill directory varies between A and B.

### Step 4: Create a fresh case workspace for every attempt

Before executing a case, create a temp parent directory and then create a brand-new
workspace for that case attempt.

Use the helper script:

```bash
bash .agents/skills/skills-evaluation/scripts/create_case_workspace.sh "<source_workspace>" "<case_workspace_root>" "<case_id>" --target "<target_id>"
```

The script returns the absolute path to the new attempt workspace.
`<source_workspace>` must be the shared workspace root that contains sibling
`agentic-evals/` and `.agents/` directories.

By default it should copy only the target skill materials needed for execution:

- the target `entry_skill`
- the target `roots`
- any explicit extra relative paths passed as additional arguments when a case needs local fixtures

The case workspace must not include repo evaluation materials such as `targets/`, `docs/`, `runs/`, or the evaluator skill itself unless a case explicitly requires them.

Rules:

- Run this once before the first attempt of every case.
- Run it again before every retry of the same case. Retries must not reuse the prior attempt workspace.
- Apply case `setup` only inside the returned workspace.
- Treat the returned workspace as a minimal target-skill sandbox, not a full clone of the eval repo.
- Resolve repo-defined files from `<source_workspace>/agentic-evals/` and target skill files from `<source_workspace>/.agents/`.
- Record the parent temp directory as `case_workspace_root` in `manifest.json`.
- Record the exact attempt workspace used for judgment as `workspace_root` in `case-results/<case_id>.json`.

In `ab-urls` mode, do this separately inside each variant run using that variant's prepared source workspace.

### Step 5: Execute each case dynamically

For every case:

1. Create a fresh isolated workspace for that case attempt under `case_workspace_root`.
2. Apply the case setup as far as the environment allows, but only inside that attempt workspace.
3. Execute the case in the selected runtime:
   - for `execution_runtime=codex`, start a fresh sub-agent with `spawn_agent` and `fork_context: false`
   - for `execution_runtime=kiro`, launch Kiro directly inside the attempt workspace from the current Codex evaluator:
     1. write the local Kiro agent config with `python3 scripts/write_kiro_hook_agent.py "<workspace_root>" --target-id "<target_id>"`
     2. set `KIRO_HOOK_TRACE_PATH` to `case-artifacts/<case_id>/raw-hook-trace.jsonl`
     3. run `kiro-cli chat --no-interactive --agent skill-eval-kiro-runtime --trust-all-tools "<case input.user_prompt>"`
     4. capture stdout to `case-artifacts/<case_id>/final-answer.txt`
     5. write `accepted-session.json` with `python3 scripts/normalize_kiro_hook_trace.py`
   - wait for Kiro to stop naturally once it has delivered its final answer; do not rely on a timeout-driven wrapper to force the handoff
4. Give the execution subject only the task-local context it needs:
   - workspace root
   - the case `input.user_prompt`
   - a requirement to answer naturally as if serving the user
5. Capture runtime metadata when available:
   - Codex agent id or nickname
   - Kiro process metadata, trace path, and exit status
6. Do not tell the execution subject which files it is expected to read.
7. Do not tell the execution subject what the correct answer should be.
8. Wait for the execution subject to finish.
9. Collect authoritative runtime evidence:
   - for Codex, locate the accepted child session JSONL from the local Codex session store using:
     - child `session_meta.payload.source.subagent.thread_spawn.parent_thread_id`
     - child start time relative to the case attempt
     - returned nickname or agent id when available
     - `~/.codex/state_5.sqlite` `thread_spawn_edges` as a locator or tie-breaker
   - for Kiro, read `case-artifacts/<case_id>/raw-hook-trace.jsonl` directly from the case artifact directory
10. If a single authoritative evidence source cannot be identified, mark the case `blocked`.
11. Write `case-artifacts/<case_id>/accepted-session.json` from the authoritative evidence for the accepted attempt.
12. Extract the accepted final answer and save it to `case-artifacts/<case_id>/final-answer.txt`.
13. Validate observed isolation before judging:
   - treat per-tool `workdir` values, resolved read and write paths, and command-derived cwd outputs such as `pwd` as the authoritative isolation signals
   - for Codex `spawn_agent`, treat child `session_meta.cwd` as advisory only, because spawned child-thread metadata may inherit the parent workspace cwd
   - for Kiro, treat hook-captured `cwd` values as authoritative when present
   - observed per-tool `workdir` values must be inside the attempt workspace
   - observed read and write paths must be inside the attempt workspace
   - if a command such as `pwd` prints a cwd, that observed cwd must be inside the attempt workspace
   - if the authoritative evidence shows an observed tool workdir, resolved path, hook `cwd`, or command-derived cwd outside the attempt workspace, invalidate that attempt, append the mismatch to `transcript.md`, create a brand-new attempt workspace, and rerun the case once
   - if no reliable tool workdir, resolved path, or command-derived cwd can be observed, mark the case `blocked`
   - if the authoritative evidence cannot support reliable isolation after the retry, mark the case `blocked`
14. Render `transcript.md` directly from the accepted evidence in event order.
15. For `execution_runtime=kiro`, have the current Codex evaluator read `codex-evaluator-prompt.md`, `evaluator-input.json`, `raw-hook-trace.jsonl`, `accepted-session.json`, `final-answer.txt`, and `isolation-report.json` before making any final judgment.
16. When the case includes evaluator-owned browser verification, the current Codex evaluator must directly use `agent-browser` as a tool. Do not hand browser verification off to a wrapper script.
   - use the globally installed `agent-browser` CLI when available
   - use a persistent `AGENT_BROWSER_HOME` so browser binaries are reused across runs
   - do not run `npx ... install` as part of normal per-case verification
   - navigate, wait, snapshot, click, and inspect console/errors with direct `agent-browser` commands from the current evaluator thread
   - write the resulting browser artifacts and `evaluator-verification.json` under `case-artifacts/<case_id>/`
17. Judge each assertion in the main evaluator from the authoritative runtime evidence preserved in `accepted-session.json`, the accepted final answer, and any evaluator-owned browser artifacts, using the rules in `AGENT.md`.
18. Write `case-artifacts/<case_id>/codex-judgment.json`, then run `scripts/finalize_codex_case_judgment.py <run_dir> <judgment_path>` to render `case-results/<case_id>.json`, `transcript.md`, and `report.md`.

In `ab-urls` mode:

1. Run the full normal case flow for variant A under `variants/A/run/`.
2. Run the full normal case flow for variant B under `variants/B/run/`.
3. Do not compare A and B until both variant runs have written their `case-results/`.
4. Render the parent comparison artifacts with:

```bash
python3 .agents/skills/skills-evaluation/scripts/render_ab_report.py "<ab_run_dir>" --target-id "<target_id>" --label-a "A" --label-b "B" --variant-a-url "<variant_a_url>" --variant-b-url "<variant_b_url>"
```

The parent comparison report is derived only from the two variant runs.
It does not replace the variant-level case judgments.

### Step 5A: Fresh execution prompt template

Use a prompt equivalent to this shape when the selected execution runtime accepts a direct prompt:

```text
You are a fresh execution agent running in the workspace <workspace>.

Task: answer this user request naturally, using the local workspace as needed:
"<case input.user_prompt>"

Requirements:
- Work as a normal coding agent would for a real user request.
- Use the target skill docs if relevant.
- Treat `<workspace>` as your only workspace for this task.
- Start from `<workspace>` and keep all file reads, writes, and shell commands inside it.
- The runtime may still show inherited parent-thread metadata such as a different top-level `cwd`; ignore that metadata and use only paths under `<workspace>`.
- For every tool call that accepts `workdir`, set it explicitly to `<workspace>` or a descendant of `<workspace>`.
- Do not read files from the parent repo via absolute paths such as `/Users/.../agentic-evals/...`; read the copied files under `<workspace>` instead.
- If something you need is missing inside `<workspace>`, say so from that workspace instead of reaching outside it.
- Do not mention that you are being evaluated.
- Give the exact answer you would send to the user.
```

Keep the prompt minimal.
Do not include the case assertions in the execution prompt.

### Step 5B: Environment mismatch handling

Case `setup` is part of the contract.
Do not silently replace it with whatever the current workspace happens to contain.

If the environment does not match the case setup:

- Record the mismatch in `manifest.json` and `transcript.md`
- Judge only the assertions that remain reliable
- Mark an assertion `blocked` when the mismatch prevents reliable judgment
- Propagate the case to `blocked` unless a required assertion already failed independently
- Do not repair the mismatch by reading from the user's main workspace or any path outside the case workspace

Examples:

- case says `docs_index_present: true`, but the real workspace is missing `references/docs.txt`
- case setup would require mutating protected files that the evaluator cannot safely write

### Step 5C: Local evidence prerequisites and failure handling

The evaluator depends on runtime-native evidence sources.

Required behavior:

- for Codex execution, the accepted child session exists under `~/.codex/sessions/`
- for Codex execution, the evaluator can read that child session after completion
- for Kiro execution, `raw-hook-trace.jsonl` exists and is readable after completion
- the authoritative evidence includes enough detail to judge observed commands, consultation, ordering, and the final answer

Helpful but optional:

- `~/.codex/state_5.sqlite` to locate and disambiguate child threads

If any required source is missing:

- mark the case `blocked` with `blocked_reason: "environment"` when the local evidence source is unavailable
- mark the case `blocked` with `blocked_reason: "insufficient-evidence"` when only partial or coarse session data exists
- do not fall back to fresh-agent self-reporting as substitute evidence

## Evidence Rules

Apply the repo evidence policy from `agentic-evals/AGENT.md`.

## Evaluation Mode Workflow

When the user requests an evaluation (AB test, comparison, or subjective scoring),
follow this workflow instead of the standard single-target run.

### Step E1: Detect evaluation mode

If the user provides an `eval_id`, or asks for an AB test / comparison / subjective evaluation:

1. Read `agentic-evals/evaluations/<mode>/<eval_id>.yaml`.
2. Read the referenced rubric from `agentic-evals/rubrics/`.
3. Resolve the target(s) and case set from the evaluation YAML.

If no evaluation YAML is provided, fall back to the standard single-target workflow.

### Step E2: Prepare variants

For each variant defined in the evaluation:

- `ab` mode: check out or copy the skill at the specified `skill_ref` into the case workspace.
  If `skill_ref` is a git tag/branch, clone the skill repo at that ref.
  If `skill_ref` is a local path, copy it.
- `comparison` mode: each variant has its own `target_id` and `skill_path`.
  Prepare each variant's skill files independently.
- `subjective` mode: single variant, use the target's current skill files.

### Step E3: Execute cases per variant

For each variant, for each case:

1. Create a fresh isolated workspace (same as standard workflow).
2. Copy the variant's skill files into the workspace.
3. Spawn a fresh subagent with the case prompt.
4. Collect evidence (same as standard workflow).
5. Judge pass/fail assertions (same as standard workflow).
6. Score each rubric dimension from the accepted session evidence.

Write variant-specific artifacts to `runs/<run_id>/variants/<variant_label>/`.

### Step E4: Score rubric dimensions

For each case and each rubric dimension:

1. Read the dimension description and anchors from the rubric.
2. Review the accepted session evidence and final answer.
3. Assign a score from the dimension's scale.
4. If evidence is insufficient, record `null` and explain in `rubric_notes`.

Scoring rules:

- Score each dimension independently.
- Use anchors for calibration: a score of 3 means "matches the anchor for 3."
- For AB and comparison modes, score each variant independently before comparing.
- Rubric scores are independent of pass/fail assertions.

### Step E5: Write evaluation report

Write `eval-report.md` with exactly these sections:

1. `Evaluation Summary` — mode, variants, case count, rubric used
2. `Scoring Table` — each case × each dimension, columns per variant
3. `Head-to-Head` — (AB and comparison only) win/loss/tie per dimension
4. `Detailed Findings` — per-case narrative of notable differences
5. `Recommendations` — at most 3 actionable items pointing to real files

For `subjective` mode, omit the `Head-to-Head` section.

Also write the standard `report.md` for backward compatibility.
For multi-variant modes, `report.md` should summarize the overall evaluation
and link to `eval-report.md` for details.

### Evaluation Manifest

`manifest.json` must additionally record:

- `eval_id`
- `eval_mode`: one of `ab`, `comparison`, `subjective`
- `variant_labels`: array of variant labels
- `rubric_id`

### AB Mode: Skill Version Preparation

For AB tests, the two variants are different versions of the same skill.
The evaluator must ensure:

- Both variants use the exact same case set.
- Each variant's workspace contains only that variant's skill files.
- The evaluator does not leak variant A's evidence into variant B's judgment.
- If a `skill_ref` cannot be resolved (e.g., git tag not found), mark all cases
  for that variant as `blocked` with `blocked_reason: "environment"`.

### Comparison Mode: Cross-Target Cases

For comparison tests, variants may reference different targets.
The `shared_cases` field specifies which target's cases to use.
The evaluator must:

- Load cases from `shared_cases.from_target`.
- For each variant, prepare the variant's own skill in the workspace.
- Run the same case prompts against each variant's skill.
- If a variant's target does not have the referenced skill files, mark its cases as `blocked`.
