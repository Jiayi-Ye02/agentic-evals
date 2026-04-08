# Evaluations

Evaluations are a higher-level orchestration layer above targets, suites, and cases.

They define **how** to run tests, not **what** to test. The "what" lives in `targets/`.

## Evaluation Modes

| Mode | Purpose | Variants |
|------|---------|----------|
| `ab` | Compare two versions of the same skill on the same cases | 2 (a, b) |
| `comparison` | Compare different vendors' skills on shared cases | 2+ |
| `subjective` | Score a single skill on rubric dimensions beyond pass/fail | 1 |

## How It Works

1. An evaluation YAML references existing targets and cases.
2. The evaluator runs each variant through the standard case execution chain
   (isolated workspace → spawn subagent → collect evidence).
3. For each case, the evaluator produces both:
   - Standard pass/fail assertions (from the case definition)
   - Rubric scores (from the referenced rubric)
4. The evaluator writes a unified `eval-report.md` with cross-variant comparison.

## File Layout

```text
evaluations/
├── ab/                           # AB tests (same skill, different versions)
│   └── <eval_id>.yaml
├── comparison/                   # Vendor comparisons (different skills, same cases)
│   └── <eval_id>.yaml
└── subjective/                   # Single-skill rubric scoring
    └── <eval_id>.yaml
```

## Relationship to Existing Concepts

- Evaluations **reference** targets and cases — they do not redefine them.
- Rubrics in `rubrics/` define scoring dimensions — evaluations reference them.
- The evaluator (skills-evaluation) handles both single-target runs and evaluation runs.
- Run artifacts go to `runs/<run_id>/` with an extended structure for multi-variant results.
