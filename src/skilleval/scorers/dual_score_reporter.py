"""
Dual-Score Reporting System

Per ADR recommendation: Report Phase 1 (packaging/security) and Phase 2 (runtime)
scores separately without renormalization.

This prevents score regression when adding Phase 2 to existing Phase 1-only skills,
and provides clear signal on both packaging quality and runtime effectiveness.
"""

from typing import Optional
from datetime import datetime

from ..models_phase1 import Phase1Score, PublishDecision
from ..models_phase2 import Phase2Score, DualScoreReport, Grade, average_grades


def create_dual_score_report(
    skill_name: str,
    skill_version: Optional[str],
    phase1: Phase1Score,
    phase2: Optional[Phase2Score] = None,
) -> DualScoreReport:
    """
    Create dual-score report from Phase 1 and optional Phase 2 results.

    Args:
        skill_name: Name of the skill
        skill_version: Skill version
        phase1: Phase 1 evaluation results
        phase2: Phase 2 evaluation results (optional)

    Returns:
        DualScoreReport with both phases
    """
    # Phase 1 data
    phase1_score = phase1.total_score
    phase1_grade = phase1.grade
    phase1_static = phase1.static.score
    phase1_security = phase1.security.score
    phase1_publish_decision = phase1.publish_decision.value
    phase1_auto_reject = phase1.auto_reject

    # Phase 2 data (if available)
    if phase2:
        phase2_score = phase2.total_score
        phase2_grade = phase2.grade
        phase2_functional = phase2.functional_score
        phase2_safety = phase2.safety_score
        total_duration = phase1.duration_seconds + phase2.duration_seconds
    else:
        # Phase 2 not run
        phase2_score = 0.0
        phase2_grade = Grade.F
        phase2_functional = 0.0
        phase2_safety = 0.0
        total_duration = phase1.duration_seconds

    # Overall grade (average of both phases if Phase 2 exists)
    if phase2:
        overall_grade = average_grades(phase1_grade, phase2_grade)
    else:
        overall_grade = phase1_grade

    # Overall recommendation
    overall_recommendation = _generate_recommendation(
        phase1, phase2, overall_grade
    )

    return DualScoreReport(
        skill_name=skill_name,
        skill_version=skill_version,
        phase1_score=phase1_score,
        phase1_grade=phase1_grade,
        phase1_static=phase1_static,
        phase1_security=phase1_security,
        phase1_publish_decision=phase1_publish_decision,
        phase1_auto_reject=phase1_auto_reject,
        phase2_score=phase2_score,
        phase2_grade=phase2_grade,
        phase2_functional=phase2_functional,
        phase2_safety=phase2_safety,
        overall_grade=overall_grade,
        overall_recommendation=overall_recommendation,
        duration_seconds=total_duration,
        timestamp=datetime.now().isoformat(),
    )


def _generate_recommendation(
    phase1: Phase1Score,
    phase2: Optional[Phase2Score],
    overall_grade: Grade,
) -> str:
    """Generate overall recommendation text."""
    lines = []

    # Phase 1 assessment
    if phase1.auto_reject:
        lines.append("❌ BLOCKED - Cannot publish due to security issues")
        lines.append(f"   {phase1.auto_reject_reason}")
        return "\n".join(lines)

    if phase1.publish_decision == PublishDecision.APPROVE:
        lines.append("✅ Packaging & Security: APPROVED")
    elif phase1.publish_decision == PublishDecision.CONDITIONAL:
        lines.append("⚠️  Packaging & Security: CONDITIONAL (publish with advisory)")
    elif phase1.publish_decision == PublishDecision.REQUIRE_ACK:
        lines.append("⚠️  Packaging & Security: Requires acknowledgment to publish")
    else:
        lines.append("❌ Packaging & Security: BLOCKED")

    # Phase 2 assessment (if run)
    if phase2:
        lines.append("")
        if phase2.grade in (Grade.A, Grade.B):
            lines.append(f"✅ Runtime Effectiveness: {phase2.grade.value} - Works well")
        elif phase2.grade == Grade.C:
            lines.append(f"⚠️  Runtime Effectiveness: {phase2.grade.value} - Works but has issues")
        elif phase2.grade == Grade.D:
            lines.append(f"⚠️  Runtime Effectiveness: {phase2.grade.value} - Significant issues")
        else:
            lines.append(f"❌ Runtime Effectiveness: {phase2.grade.value} - Does not work correctly")

        # Specific issues
        if phase2.infinite_loops_detected > 0:
            lines.append(f"   ⚠️  {phase2.infinite_loops_detected} infinite loop(s) detected")
        if phase2.hallucinations_detected > 0:
            lines.append(f"   ⚠️  {phase2.hallucinations_detected} hallucination(s) detected")
        if phase2.context_rot_detected > 0:
            lines.append(f"   ⚠️  {phase2.context_rot_detected} context rot issue(s)")

    # Overall
    lines.append("")
    lines.append(f"Overall Grade: {overall_grade.value}")

    if overall_grade == Grade.A:
        lines.append("Excellent skill - well-packaged, secure, and effective at runtime")
    elif overall_grade == Grade.B:
        lines.append("Good skill - ready for use with minor improvements possible")
    elif overall_grade == Grade.C:
        lines.append("Acceptable skill - usable but improvements recommended")
    elif overall_grade == Grade.D:
        lines.append("Needs improvement - significant issues to address")
    else:
        lines.append("Not ready for production use")

    return "\n".join(lines)


def format_dual_score_report(report: DualScoreReport) -> str:
    """Format dual-score report as human-readable text."""
    lines = []

    lines.append("=" * 80)
    lines.append("DUAL-SCORE EVALUATION REPORT")
    lines.append("Phase 1 (Packaging & Security) + Phase 2 (Runtime Effectiveness)")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Skill: {report.skill_name}")
    if report.skill_version:
        lines.append(f"Version: {report.skill_version}")
    lines.append(f"Timestamp: {report.timestamp}")
    lines.append(f"Duration: {report.duration_seconds:.1f}s")
    lines.append("")

    # Overall Summary
    lines.append("-" * 80)
    lines.append("OVERALL ASSESSMENT")
    lines.append("-" * 80)
    lines.append(f"Overall Grade: {report.overall_grade.value}")
    lines.append("")
    lines.append(report.overall_recommendation)
    lines.append("")

    # Phase 1 Details
    lines.append("-" * 80)
    lines.append("PHASE 1: PACKAGING & SECURITY")
    lines.append("-" * 80)
    lines.append(f"Total Score: {report.phase1_score:.1f}/100 (Grade {report.phase1_grade.value})")
    lines.append(f"Publish Decision: {report.phase1_publish_decision}")
    if report.phase1_auto_reject:
        lines.append("⚠️  AUTO-REJECTED due to security issues")
    lines.append("")
    lines.append("Breakdown:")
    lines.append(f"  Static Tests (ST-1 through ST-8):  {report.phase1_static:.1f}/50")
    lines.append(f"  Security (Layer 1 + Layer 2):      {report.phase1_security:.1f}/50")
    lines.append("")

    # Phase 2 Details (if available)
    if report.phase2_score > 0:
        lines.append("-" * 80)
        lines.append("PHASE 2: RUNTIME EFFECTIVENESS")
        lines.append("-" * 80)
        lines.append(f"Total Score: {report.phase2_score:.1f}/100 (Grade {report.phase2_grade.value})")
        lines.append("")
        lines.append("Breakdown:")
        lines.append(f"  Functional Correctness:  {report.phase2_functional:.1f}/50")
        lines.append(f"  LLM Safety:              {report.phase2_safety:.1f}/50")
        lines.append("")
    else:
        lines.append("-" * 80)
        lines.append("PHASE 2: NOT RUN")
        lines.append("-" * 80)
        lines.append("Runtime evaluation was not performed.")
        lines.append("Run with harness evaluation enabled to get Phase 2 scores.")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def format_summary_table(report: DualScoreReport) -> str:
    """Format a compact summary table."""
    lines = []

    lines.append("┌" + "─" * 78 + "┐")
    lines.append(f"│ {'Skill Evaluation Summary':<76} │")
    lines.append("├" + "─" * 78 + "┤")
    lines.append(f"│ Skill: {report.skill_name:<67} │")
    lines.append(f"│ Overall Grade: {report.overall_grade.value:<61} │")
    lines.append("├" + "─" * 38 + "┬" + "─" * 39 + "┤")
    lines.append(f"│ {'PHASE 1: Packaging & Security':<37} │ {'PHASE 2: Runtime':<38} │")
    lines.append("├" + "─" * 38 + "┼" + "─" * 39 + "┤")
    lines.append(f"│ Score: {report.phase1_score:>5.1f}/100  Grade: {report.phase1_grade.value:<5} │ Score: {report.phase2_score:>5.1f}/100  Grade: {report.phase2_grade.value:<5} │")
    lines.append(f"│ Static:   {report.phase1_static:>5.1f}/50{'':<19} │ Functional: {report.phase2_functional:>5.1f}/50{'':<14} │")
    lines.append(f"│ Security: {report.phase1_security:>5.1f}/50{'':<19} │ Safety:     {report.phase2_safety:>5.1f}/50{'':<14} │")
    lines.append("└" + "─" * 38 + "┴" + "─" * 39 + "┘")

    return "\n".join(lines)
