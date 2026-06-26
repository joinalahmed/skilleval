# Quick Start Guide

Get started with the ADR-compliant Phase 1 + Phase 2 evaluation framework in 5 minutes.

---

## Installation

```bash
cd /path/to/skilleval

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Verify installation
python3 evaluate_skill.py --help
```

---

## Basic Usage

### Evaluate a Single Skill (Phase 1 Only)

```bash
python3 evaluate_skill.py /path/to/skill --phase1-only
```

**What it does**:
- ✅ Runs ST-1 through ST-8 static tests (50 points)
- ✅ Runs Layer 1 security scan (18 checks, 50 points)
- ✅ Produces 0-100 score with A-F grade
- ✅ Shows publish decision (APPROVE, CONDITIONAL, REQUIRE_ACK, BLOCK)
- ⚡ **Fast**: <1 second, no LLM calls

**Example output**:
```
Total Score: 91.0/100
Grade: A
Publish Decision: APPROVE

PILLAR 1: STATIC TESTS (50 points)
Score: 49.0/50 (Grade A)

PILLAR 2: SECURITY (50 points)
Score: 42.0/50 (Grade B)

✅ APPROVED - Ready to publish
   Eligible for featured listing
```

---

### Full Evaluation (Phase 1 + Phase 2)

```bash
python3 evaluate_skill.py /path/to/skill --full
```

**What it does**:
- ✅ Phase 1: Static + Security (as above)
- ⏳ Phase 2: Harness evaluation (coming soon)
  - Baseline vs skill comparison
  - Deterministic LLM safety checks
  - Functional correctness grading

**Note**: Phase 2 integration pending. Currently use:
```bash
python3 -m skilleval.cli eval /path/to/skill
```

---

## Output Formats

### Text (default)

```bash
python3 evaluate_skill.py /path/to/skill --phase1-only
```

Human-readable report printed to stdout.

### JSON

```bash
python3 evaluate_skill.py /path/to/skill --phase1-only --format json
```

Machine-readable JSON for tooling integration.

### Both

```bash
python3 evaluate_skill.py /path/to/skill --phase1-only --format both
```

Text to stdout + JSON saved to file.

### Save to File

```bash
python3 evaluate_skill.py /path/to/skill --phase1-only --output report.json
```

---

## Interpreting Results

### Grade Scale

| Grade | Score | Meaning |
|-------|-------|---------|
| **A** | 90-100 | Excellent - publish-ready, featured eligible |
| **B** | 80-89  | Good - ready for production |
| **C** | 70-79  | Acceptable - publish with advisory |
| **D** | 60-69  | Needs improvement - requires acknowledgment |
| **F** | 0-59   | Blocked - cannot publish |

### Publish Decisions

- **APPROVE**: Skill meets quality bar, publish immediately
- **CONDITIONAL**: Publish with advisory warnings shown to users
- **REQUIRE_ACK**: Author must explicitly confirm "publish anyway"
- **BLOCK**: Cannot publish until issues resolved

### Auto-Reject Triggers

Your skill is **automatically rejected** (Grade F) if:
1. Any **CRITICAL** security finding with confidence >= 0.7
2. Security score < 25/50 (50% floor)

---

## Common Issues & Fixes

### Low Static Score

**Issue**: `ST-1 Frontmatter: 6.0/12`

**Fix**: Add missing frontmatter fields:
```yaml
---
name: my-skill
description: At least 20 characters describing what this skill does
version: 1.0.0
author: Your Name
tags: [automation, productivity]
---
```

**Issue**: `ST-5 Eval Suite: 3.0/8 - Only 1 eval cases (need 3+)`

**Fix**: Add more test cases to `evals.json`:
```json
{
  "eval_cases": [
    {"id": "1", "prompt": "...", "expected_output": "...", "graders": [...]},
    {"id": "2", "prompt": "...", "expected_output": "...", "graders": [...]},
    {"id": "3", "prompt": "...", "expected_output": "...", "graders": [...]}
  ]
}
```

### Security Findings

**Finding**: `[MEDIUM] Credential file reference: \.env (conf=0.60, penalty=3.0)`

**Why**: References to `.env` files are flagged as potential credential leakage.

**Fix**:
- If it's documentation/examples: Confidence is lower (0.4), becomes advisory only
- If it's actual code loading `.env`: Consider if this is necessary
- Add comment explaining it's for local dev only

**Finding**: `[HIGH] Hardcoded API key detected (conf=0.95)`

**Why**: Pattern like `sk-abc123...` detected outside code blocks.

**Fix**:
- Remove the actual key
- Replace with placeholder: `sk-example-key-replace-this`
- Use environment variables: `API_KEY = os.getenv("OPENAI_API_KEY")`

**Finding**: `[CRITICAL] Dangerous YAML tag: !!python/object (conf=0.95)`

**Why**: YAML deserialization RCE vulnerability.

**Fix**:
- Remove `!!python/object` and `!!python/apply` tags
- Use safe YAML loading: `yaml.safe_load()`

---

## Batch Evaluation

Evaluate multiple skills:

```bash
#!/bin/bash
for skill in /path/to/skills-hub/skills/*; do
    skill_name=$(basename "$skill")
    echo "Evaluating: $skill_name"
    
    python3 evaluate_skill.py "$skill" \
        --phase1-only \
        --output "reports/${skill_name}_phase1.json" \
        --format both
    
    echo "---"
done
```

---

## Advanced Usage

### Custom Skill Path

```bash
python3 evaluate_skill.py ~/my-skills/custom-skill --phase1-only
```

### Exit Codes

- `0`: Skill passed (Grade A-D)
- `1`: Skill failed (Grade F or auto-reject)

Use in CI/CD:
```bash
if python3 evaluate_skill.py /path/to/skill --phase1-only; then
    echo "✅ Skill quality check passed"
else
    echo "❌ Skill quality check failed"
    exit 1
fi
```

---

## Troubleshooting

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'skilleval'`

**Fix**:
```bash
cd /path/to/skilleval
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python3 evaluate_skill.py /path/to/skill --phase1-only
```

Or run with absolute path:
```bash
cd /path/to/skilleval
python3 $(pwd)/evaluate_skill.py /path/to/skill --phase1-only
```

### SKILL.md Not Found

**Error**: `Error: SKILL.md not found in /path/to/skill`

**Fix**: Ensure your skill directory contains `SKILL.md`:
```
my-skill/
├── SKILL.md          ← Required
├── evals.json        ← Recommended (for ST-5 score)
├── scripts/          ← Optional
└── references/       ← Optional
```

### Warnings

**Warning**: `Field name "schema" in "Grader" shadows an attribute in parent "BaseModel"`

**Impact**: None. This is a Pydantic internal warning that doesn't affect functionality.

---

## What's Next?

### For Skill Authors

1. **Run Phase 1** on your skill
2. **Fix issues** flagged in the report
3. **Iterate** until Grade A or B
4. **Publish** with confidence

### For Framework Developers

1. **Integrate Phase 2** into `evaluate_skill.py --full`
2. **Add SkillSpector** (Layer 2 security scanning)
3. **Calibrate thresholds** on 109-skill corpus
4. **Generate HTML reports** with visualizations

---

## Reference

- **Full Architecture**: See [PHASE1_PHASE2_ARCHITECTURE.md](./PHASE1_PHASE2_ARCHITECTURE.md)
- **ADR**: Original architecture decision record
- **Production Results**: See [PRODUCTION_EVALUATION_RESULTS.md](./PRODUCTION_EVALUATION_RESULTS.md)

---

**Status**: ✅ Phase 1 ready for production use
**Date**: 2026-06-23
**Support**: File issues at [GitHub repo]
