#!/usr/bin/env python3
"""
Unified Skill Evaluation CLI

Runs Phase 1 (Static + Security) and optionally Phase 2 (Harness).
Produces dual-score report per ADR specification.

Usage:
    python3 evaluate_skill.py /path/to/skill --phase1-only
    python3 evaluate_skill.py /path/to/skill --full
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from skilleval.scorers.phase1_orchestrator import Phase1Orchestrator, format_phase1_report
from skilleval.scorers.dual_score_reporter import (
    create_dual_score_report,
    format_dual_score_report,
    format_summary_table,
)
from skilleval.models_phase1 import Phase1Score
from skilleval.models_phase2 import Phase2Score


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a skill using Phase 1 (Static + Security) and optionally Phase 2 (Harness)"
    )
    parser.add_argument(
        "skill_path",
        type=Path,
        help="Path to skill directory containing SKILL.md",
    )
    parser.add_argument(
        "--phase1-only",
        action="store_true",
        help="Run Phase 1 only (Static + Security)",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run both Phase 1 and Phase 2",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON report (default: print to stdout)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text", "both"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    if not args.skill_path.exists():
        print(f"Error: Skill path does not exist: {args.skill_path}", file=sys.stderr)
        sys.exit(1)

    skill_md = args.skill_path / "SKILL.md"
    if not skill_md.exists():
        print(f"Error: SKILL.md not found in {args.skill_path}", file=sys.stderr)
        sys.exit(1)

    # Extract skill name from path or frontmatter
    skill_name = args.skill_path.name

    # Only print progress if text output
    if args.format in ("text", "both"):
        print(f"Evaluating skill: {skill_name}")
        print(f"Path: {args.skill_path}")
        print("")

    # ========================================================================
    # Phase 1: Static + Security (ADR: 50 + 50 = 100 points)
    # ========================================================================
    # Per ADR:
    # - Static Tests (ST-1 through ST-8): 50 points (additive)
    # - Security (Layer 1 + Layer 2): 50 points (deductive, confidence-weighted)
    # - Total: 0-100 with A-F grading
    # - Publish decision: APPROVE/CONDITIONAL/REQUIRE_ACK/BLOCK

    if args.format in ("text", "both"):
        print("=" * 70)
        print("PHASE 1: STATIC TESTS + SECURITY")
        print("=" * 70)
        print("")

    orchestrator = Phase1Orchestrator(args.skill_path)
    phase1_result = orchestrator.evaluate()

    if args.format in ("text", "both"):
        print(format_phase1_report(phase1_result))
        print("")

    # ========================================================================
    # Phase 2: Harness Evaluation (ADR: 50 + 50 = 100 points)
    # ========================================================================
    # Per ADR:
    # - Functional Correctness: 50 points (baseline vs skill, deterministic graders)
    # - LLM Safety: 50 points (deductive, deterministic trace analysis)
    # - Total: 0-100 with A-F grading
    # - Calibrated thresholds from production data (jira-comment-poster)
    # - NO LLM-as-judge (all deterministic)

    phase2_result = None

    if args.full and not args.phase1_only:
        if args.format in ("text", "both"):
            print("=" * 70)
            print("PHASE 2: HARNESS EVALUATION")
            print("=" * 70)
            print("")
            print("Running baseline vs skill comparison with real LLM agents...")
            print("This will take several minutes depending on eval cases.")
            print("")
            print("ADR Model:")
            print("  - Functional: 50 points (skill improvement over baseline)")
            print("  - Safety: 50 points (deterministic trace analysis)")
            print("  - Thresholds: max_turns=15, context_rot=200K tokens")
            print("")

        # Run Phase 2 (Harness) using existing orchestrator
        from skilleval.orchestrator import Orchestrator
        from skilleval.models import Config
        from skilleval.utils.skill_loader import load_skill

        # Configure with ADR weights (30/30/40)
        config = Config()
        config.scoring.weights = {
            "static_tests": 0.30,
            "security": 0.30,
            "harness": 0.40,
        }

        orchestrator = Orchestrator(config)

        # Load skill and run harness only (we already ran Phase 1)
        from skilleval.pillars.harness import HarnessPillar

        skill = load_skill(args.skill_path)
        harness_pillar = HarnessPillar(config.harness)
        harness_result = harness_pillar.run(args.skill_path, skill.eval_cases)

        # Convert to Phase2Score format using ADR model
        from skilleval.scorers.harness_scorer import HarnessScorer
        from skilleval.models_phase2 import FunctionalCaseResult, SafetyCheck as NewSafetyCheck, Severity

        scorer = HarnessScorer()

        # Convert old FunctionalResult to new FunctionalCaseResult
        functional_cases = []
        for old_result in harness_result.functional_results:
            # Calculate improvement (skill score - baseline score)
            baseline_score = getattr(old_result, 'baseline_score', 0.0)
            skill_score = getattr(old_result, 'skill_score', 0.0)
            improvement = skill_score - baseline_score
            improvement_pct = (improvement / 100.0) * 100.0 if improvement != 0 else 0.0

            functional_cases.append(FunctionalCaseResult(
                case_id=old_result.case_id,
                baseline_score=baseline_score,
                skill_score=skill_score,
                improvement=improvement,
                improvement_pct=improvement_pct,
                baseline_checks=[],  # Old model doesn't have grader results
                skill_checks=[],
            ))

        # Convert old SafetyCheck to new SafetyCheck
        new_safety_checks = []
        total_cost = 0.0
        total_tokens = 0

        for old_check in harness_result.safety_checks:
            # Extract fields from old model
            check_id = getattr(old_check, 'check', 'unknown')
            severity_val = getattr(old_check, 'severity', 'INFO')
            score = getattr(old_check, 'score', 100.0)
            details = getattr(old_check, 'details', {})

            # Accumulate cost and tokens
            if 'cost' in details:
                total_cost += details['cost']
            if 'total_tokens' in details:
                total_tokens += details['total_tokens']

            # Convert severity string to enum
            if isinstance(severity_val, str):
                severity = Severity[severity_val] if severity_val in Severity.__members__ else Severity.INFO
            else:
                severity = severity_val

            # Determine passed based on score (old model: score < 100 = failed)
            passed = score >= 100

            # Create message from details
            message = details.get('message', f"{check_id}: {'passed' if passed else 'failed'}")

            new_safety_checks.append(NewSafetyCheck(
                check_id=check_id,
                label=old_check.case_id if hasattr(old_check, 'case_id') else check_id,
                severity=severity,
                passed=passed,
                score=score,
                message=message,
                details=details,
            ))

        phase2_result = scorer.score(
            functional_cases=functional_cases,
            safety_checks=new_safety_checks,
            total_cost=total_cost,
            total_tokens=total_tokens,
            duration_seconds=harness_result.duration_seconds,
        )

        if args.format in ("text", "both"):
            print(f"Phase 2 complete: {phase2_result.total_score:.1f}/100 (Grade {phase2_result.grade.value})")
            print(f"  Functional: {phase2_result.functional_score:.1f}/50")
            print(f"  Safety:     {phase2_result.safety_score:.1f}/50")
            print(f"  Duration:   {phase2_result.duration_seconds:.1f}s")
            print("")

    # ========================================================================
    # Output Generation
    # ========================================================================

    # For Phase 1 only with JSON output
    if args.phase1_only and (args.format == "json" or args.output):
        report_json = {
            "skill_name": skill_name,
            "timestamp": datetime.now().isoformat(),
            "phase1": {
                "score": phase1_result.total_score,
                "grade": phase1_result.grade.value,
                "static": phase1_result.static.score,
                "security": phase1_result.security.score,
                "publish_decision": phase1_result.publish_decision.value,
                "auto_reject": phase1_result.auto_reject,
            },
        }

        if args.output:
            args.output.write_text(json.dumps(report_json, indent=2))
            if args.format in ("text", "both"):
                print(f"\nReport saved to: {args.output}")
        elif args.format == "json":
            print(json.dumps(report_json, indent=2))

    # ========================================================================
    # Dual-Score Report (ADR: No Renormalization)
    # ========================================================================
    # Per ADR recommendation:
    # - Show Phase 1 (packaging/security) and Phase 2 (runtime) separately
    # - NO renormalization (prevents score regression)
    # - Overall grade = average of Phase 1 and Phase 2
    # - Both scores visible to show packaging quality vs runtime effectiveness

    if args.full or phase2_result:
        if args.format in ("text", "both"):
            print("=" * 70)
            print("DUAL-SCORE REPORT (ADR-Compliant)")
            print("=" * 70)
            print("")
            print("NOTE: Both phases shown separately (no renormalization).")
            print("This prevents score regression and provides clear signal on")
            print("packaging quality vs runtime effectiveness.")
            print("")

        dual_report = create_dual_score_report(
            skill_name=skill_name,
            skill_version=None,
            phase1=phase1_result,
            phase2=phase2_result,
        )

        if args.format in ("text", "both"):
            print(format_summary_table(dual_report))
            print("")
            print(format_dual_score_report(dual_report))

        # Save JSON
        if args.output or args.format in ("json", "both"):
            report_json = {
                "skill_name": skill_name,
                "timestamp": datetime.now().isoformat(),
                "phase1": {
                    "score": phase1_result.total_score,
                    "grade": phase1_result.grade.value,
                    "static": phase1_result.static.score,
                    "security": phase1_result.security.score,
                    "publish_decision": phase1_result.publish_decision.value,
                    "auto_reject": phase1_result.auto_reject,
                },
                "phase2": {
                    "score": phase2_result.total_score if phase2_result else 0.0,
                    "grade": phase2_result.grade.value if phase2_result else "F",
                    "functional": phase2_result.functional_score if phase2_result else 0.0,
                    "safety": phase2_result.safety_score if phase2_result else 0.0,
                } if phase2_result else None,
                "overall_grade": dual_report.overall_grade.value if phase2_result else phase1_result.grade.value,
            }

            if args.output:
                args.output.write_text(json.dumps(report_json, indent=2))
                print(f"Report saved to: {args.output}")
            elif args.format in ("json", "both"):
                print(json.dumps(report_json, indent=2))

    # Exit code based on result
    if phase1_result.auto_reject:
        sys.exit(1)  # Auto-reject
    elif phase1_result.grade.value == "F":
        sys.exit(1)  # Failed
    else:
        sys.exit(0)  # Passed


if __name__ == "__main__":
    main()
