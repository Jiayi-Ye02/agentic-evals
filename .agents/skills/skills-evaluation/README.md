# skills-evaluation

`skill-eval` skill is the runner for the `agentic-evals` protocol.
It does not define what is correct to test. The `agentic-evals` repo defines targets,
suites, cases, assertions, and output format.

If you only remember one thing, remember this:

`agentic-evals` defines what to test, `skill-eval` runs the test, and a fresh execution
subject is the thing being judged.

## Skill Repo Layout

```text
README.md
agentic-evals/
├── AGENT.md
├── docs/
└── targets/
.agents/
└── skills/
    └── skills-evaluation/
        ├── SKILL.md
        ├── references/
        └── scripts/
```

## Install

Install `skill-eval` with:

```bash
npx skills add Jiayi-Ye02/skills-evaluation --skill skill-eval
```

- `skill-eval`: runs the `agentic-evals` evaluation repo against a target skill,
  collects per-case results, and writes a short report

It now supports:

- `single-run`: one target skill version
- `ab-urls`: two target skill versions supplied as GitHub HTTP URLs

## Framework Structure

In a normal run there are 4 separate roles:

1. `agentic-evals/`
   The test repo and source of truth for targets, suites, cases, assertions, and report contract.
2. `skill-eval`
   The evaluator skill that executes the repo-defined protocol.
3. target skill
   The skill under test, for example `.agents/skills/<target-skill>/`.
4. fresh execution subject
   The execution subject that receives the case prompt and produces the trace and answer to judge.
   This may be a fresh Codex sub-agent or a Kiro run with raw hook tracing enabled.

That separation matters:

- the test repo decides pass/fail rules
- the evaluator runs the process
- the fresh sub-agent is what actually gets tested

### Expected Workspace Layout

Your workspace will normally look like this:

```text
<workspace>/
├── .agents/
│   └── skills/
│       ├── <target-skill>/
│       └── skills-evaluation/
├── agentic-evals/
└── ...
```

## Requirements

- Codex evaluator runtime
- Codex with `spawn_agent` available when `execution_runtime=codex`
- Kiro CLI with hook support when `execution_runtime=kiro`
- Codex CLI is supported when it can create child sessions and write normal session artifacts under `~/.codex`
- `git`
- `bash`
- local target skill files
- local `agentic-evals` repo, or network access so it can be cloned if missing

## Execution Runtime Support

`skill-eval` keeps Codex as the evaluator.
The execution runtime under test may be Codex or Kiro.

Validated Codex execution expectations:

- `multi_agent` is enabled
- the runtime can create a fresh child session
- `~/.codex/sessions/` receives the child session JSONL
- `~/.codex/state_5.sqlite` records the parent-child link in `thread_spawn_edges`

Validated Kiro execution expectations:

- Kiro can run in the isolated case workspace
- Kiro hooks can append raw JSON lines to `case-artifacts/<case_id>/raw-hook-trace.jsonl`
- the evaluator can capture the final answer into `case-artifacts/<case_id>/final-answer.txt`
- the evaluator can write `accepted-session.json` from the raw hook trace without semantic normalization

Important boundaries:

- for `execution_runtime=codex`, per-case execution must still use `spawn_agent`
- for `execution_runtime=kiro`, Codex remains the judge and must evaluate the Kiro run from raw hook traces
- `accepted-session.json` is the canonical raw judge artifact for both Codex and Kiro runs
- `codex exec` may be used only as an environment smoke test, not as a substitute for case execution
- if `~/.codex` is read-only, or login/network state prevents normal Codex sessions, treat Codex execution as environment-blocked
- if Kiro hooks cannot emit raw traces reliably, treat Kiro execution as environment-blocked

## Quickstart

Once you have workspace prepared, ask Codex in plain language to use `skill-eval`. For example::

Single case:

```text
Use skill-eval to test target_id=voice-ai-integration, case_id=convoai-phase1-only-before-gates.
```

Single case with Kiro execution:

```text
Use skill-eval to test target_id=voice-ai-integration, case_id=convoai-phase1-only-before-gates, execution_runtime=kiro.
```

Preferred Kiro execution path:

- keep Codex in the current thread as the evaluator
- extract the case `input.user_prompt` verbatim
- write the local Kiro agent config with `scripts/write_kiro_hook_agent.py`
- launch `kiro-cli chat` directly inside the isolated case workspace
- capture stdout to `final-answer.txt`
- write `accepted-session.json` from the raw hook trace and judge from that canonical raw artifact after Kiro stops naturally

Single suite:

```text
Use skill-eval to test target_id=voice-ai-integration, suite=source-order.
```

Default target with default suites:

```text
Use skill-eval to run the default target with its default suites.
```

Chinese example:

```text
用 skill-eval 去测试 target_id=voice-ai-integration，测试范围 case_id=convoai-phase1-only-before-gates
```

A/B URL mode:

```text
Use skill-eval in ab-urls mode for target_id=voice-ai-integration.
variant_a_url=https://github.com/org/repo/tree/main/.agents/skills/voice-ai-integration
variant_b_url=https://github.com/org/repo/tree/rewrite/.agents/skills/voice-ai-integration
case_id=auth-prefers-rtc-token
```

Chinese A/B example:

```text
用 skill-eval 以 ab-urls 模式测试 target_id=voice-ai-integration。
variant_a_url=https://github.com/org/repo/tree/main/.agents/skills/voice-ai-integration
variant_b_url=https://github.com/org/repo/tree/rewrite/.agents/skills/voice-ai-integration
suite_id=convoai-api
```

## 5-Minute Mental Model

When you ask Codex to run an eval, the expected flow is:

1. Codex uses `skill-eval`.
2. `skill-eval` reads `agentic-evals/AGENT.md` and `agentic-evals/docs/session-evidence.md`.
3. It resolves the target from `agentic-evals/targets/<target_id>/target.yaml`.
4. It reads the selected suite and case files from `agentic-evals/targets/<target_id>/`.
5. It creates a new run directory under `agentic-evals/runs/<run_id>/`.
6. For each case, it creates a brand-new isolated temp workspace.
7. It executes the case in the selected runtime.
8. The evaluator captures authoritative runtime evidence and extracts the final user-facing answer.
9. For Kiro runs, the evaluator first collects `raw-hook-trace.jsonl`, `accepted-session.json`, `final-answer.txt`, `isolation-report.json`, and `evaluator-input.json`.
10. Codex then reads those artifacts and writes the final `case-results/<case_id>.json`, `transcript.md`, and `report.md`.
11. The evaluator writes final artifacts under `agentic-evals/runs/<run_id>/`.

In `ab-urls` mode, steps 6-10 happen twice, once for A and once for B, and then the evaluator writes a parent comparison report.

## What To Expect During A Run

During execution, the evaluator should:

- report which target, suite, or case it is using
- create a fresh case workspace under a temp directory
- execute the case in the selected runtime
- tell you the sub-agent nickname or id when the selected runtime is Codex
- write artifacts under `agentic-evals/runs/<run_id>/`

The evaluator should not:

- run the case directly in your main workspace
- silently replace the fresh sub-agent with a fallback executor
- mark `pass` from a vague self-report alone

## Run Artifacts

Every run should create:

```text
agentic-evals/runs/<run_id>/
├── manifest.json
├── case-artifacts/
├── transcript.md
├── case-results/
└── report.md
```

- `report.md`: short summary and next actions
- `case-results/<case_id>.json`: official status for one case
- `transcript.md`: readable transcript rendered from accepted evidence
- `manifest.json`: run metadata, workspace mode, and environment mismatch notes

When `execution_runtime=kiro`, each case should also retain `case-artifacts/<case_id>/raw-hook-trace.jsonl` as the capture trace, with `accepted-session.json` storing the same accepted raw events in the canonical judge artifact path.

In `ab-urls` mode the parent run additionally contains:

```text
agentic-evals/runs/<ab_run_id>/
├── manifest.json
├── variants/
│   ├── A/
│   │   ├── source-manifest.json
│   │   └── run/
│   └── B/
│       ├── source-manifest.json
│       └── run/
├── comparison.json
└── report.md
```

Helper scripts for this mode:

- `.agents/skills/skills-evaluation/scripts/parse_github_skill_url.py`
- `.agents/skills/skills-evaluation/scripts/prepare_variant_source_workspace.py`
- `.agents/skills/skills-evaluation/scripts/init_ab_run.py`
- `.agents/skills/skills-evaluation/scripts/render_ab_report.py`
