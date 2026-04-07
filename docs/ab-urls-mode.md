# A/B URL Mode

This note describes the intended integration points for the `ab-urls` run mode.

## Purpose

`ab-urls` compares two versions of the same target skill by running the same selected
case set twice and then comparing the two result sets.

Inputs:

- `target_id`
- `variant_a_url`
- `variant_b_url`
- optional `label_a`
- optional `label_b`
- optional `suite_ids` or `case_ids`

## URL Expectations

Preferred GitHub URL formats:

- `https://github.com/<org>/<repo>/tree/<ref>/<skill-dir>`
- `https://github.com/<org>/<repo>/blob/<ref>/<skill-dir>/SKILL.md`

The repo helper `scripts/parse_github_skill_url.py` resolves:

- `repo_url`
- `ref`
- `subdir`

It uses `git ls-remote` so branch names with `/` can still be resolved correctly.

## Variant Source Workspace

Each variant gets its own prepared source workspace:

```text
<prepared-source>/
├── agentic-evals/
└── .agents/
    └── skills/
        └── <target_id>/
```

The repo helper `scripts/prepare_variant_source_workspace.py` creates this layout.

## Parent Run Setup

The repo helper `scripts/init_ab_run.py` initializes:

```text
runs/<ab_run_id>/
├── manifest.json
├── variants/
│   ├── A/
│   │   ├── source-manifest.json
│   │   └── run/
│   └── B/
│       ├── source-manifest.json
│       └── run/
└── report.md
```

Each variant run under `variants/<label>/run/` is expected to satisfy the normal
`single-run` artifact contract from `AGENT.md`.

## Comparison Rendering

After both variant runs complete, call:

```bash
python3 agentic-evals/scripts/render_ab_report.py \
  "<ab_run_dir>" \
  --target-id "<target_id>" \
  --label-a "A" \
  --label-b "B" \
  --variant-a-url "<variant_a_url>" \
  --variant-b-url "<variant_b_url>"
```

This writes:

- `comparison.json`
- parent `report.md`

## Skill-Eval Integration Touchpoints

The evaluator skill should eventually do the following when it detects `ab-urls` mode:

1. Read the normal target contract and selected cases.
2. Call `scripts/init_ab_run.py`.
3. For each variant:
   - read `variants/<label>/source-manifest.json`
   - use that variant's prepared source workspace as the `source_workspace`
   - run the normal per-case `spawn_agent` evaluator flow into `variants/<label>/run/`
4. Call `scripts/render_ab_report.py`.

This repo note exists so the repo-side protocol can be implemented even when the
local `skill-eval` files are not writable in the current environment.
