"""
Phase 1 Orchestrator

Combines Static Tests (50 pts) + Security (50 pts) into unified Phase 1 score.
Produces 0-100 score with A-F grading and publish decision.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from ..models_phase1 import (
    Phase1Score,
    Phase1StaticScore,
    Phase1SecurityScore,
    Grade,
    PublishDecision,
    score_to_grade,
    grade_to_publish_decision,
)
from .static_scorer import StaticTestsScorer
from .security_scorer import SecurityScorer


class Phase1Orchestrator:
    """Orchestrates Phase 1 evaluation: Static (50) + Security (50) = 100."""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir

    def evaluate(self) -> Phase1Score:
        """Run Phase 1 evaluation and return combined score."""
        start_time = datetime.now()

        # Run Static Tests (Pillar 1)
        static_scorer = StaticTestsScorer(self.skill_dir)
        static_result = static_scorer.score()

        # Run Security (Pillar 2)
        security_scorer = SecurityScorer(self.skill_dir)
        security_result = security_scorer.score()

        # Compute total score
        total_score = static_result.score + security_result.score

        # Determine overall grade
        grade = score_to_grade(total_score, max_score=100)

        # Check auto-reject
        auto_reject = security_result.auto_reject
        auto_reject_reason = None

        if security_result.has_critical_high_conf:
            auto_reject_reason = (
                "CRITICAL security finding with high confidence (>= 0.7) detected"
            )
        elif security_result.below_security_floor:
            auto_reject_reason = (
                f"Security score {security_result.score:.1f}/50 below 50% floor"
            )

        # Determine publish decision
        publish_decision = grade_to_publish_decision(grade, auto_reject)

        duration = (datetime.now() - start_time).total_seconds()

        return Phase1Score(
            static=static_result,
            security=security_result,
            total_score=total_score,
            grade=grade,
            publish_decision=publish_decision,
            auto_reject=auto_reject,
            auto_reject_reason=auto_reject_reason,
            duration_seconds=duration,
            timestamp=datetime.now().isoformat(),
        )


def format_phase1_report(score: Phase1Score) -> str:
    """Format Phase 1 score as human-readable report."""
    lines = []

    lines.append("=" * 70)
    lines.append("PHASE 1 EVALUATION REPORT")
    lines.append("Static Tests + Security Analysis")
    lines.append("=" * 70)
    lines.append("")

    # Overall Score
    lines.append(f"Total Score: {score.total_score:.1f}/100")
    lines.append(f"Grade: {score.grade.value}")
    lines.append(f"Publish Decision: {score.publish_decision.value}")

    if score.auto_reject:
        lines.append(f"⚠️  AUTO-REJECT: {score.auto_reject_reason}")

    lines.append("")
    lines.append(f"Duration: {score.duration_seconds:.2f}s")
    lines.append(f"Timestamp: {score.timestamp}")
    lines.append("")

    # Pillar Breakdown
    lines.append("-" * 70)
    lines.append("PILLAR 1: STATIC TESTS (50 points)")
    lines.append("-" * 70)
    lines.append(f"Score: {score.static.score:.1f}/50 (Grade {score.static.grade.value})")
    lines.append("")
    lines.append("Breakdown:")
    lines.append(f"  ST-1 Frontmatter:     {score.static.st1_frontmatter:.1f}/12")
    lines.append(f"  ST-2 Description:     {score.static.st2_description:.1f}/10")
    lines.append(f"  ST-3 Completeness:    {score.static.st3_completeness:.1f}/8")
    lines.append(f"  ST-4 Script Quality:  {score.static.st4_script_quality:.1f}/8")
    lines.append(f"  ST-5 Eval Suite:      {score.static.st5_eval_suite:.1f}/8")
    lines.append(f"  ST-6 Clarity:         {score.static.st6_clarity:.1f}/4")
    lines.append(f"  ST-7 Specificity:     {score.static.st7_specificity:.1f}/6 (bonus)")
    lines.append(f"  ST-8 Cross-Ref:       {score.static.st8_cross_reference:.1f}/4 (bonus)")

    if score.static.total_before_cap > 50:
        lines.append(f"  Total before cap:     {score.static.total_before_cap:.1f}")
        lines.append(f"  Final (capped):       {score.static.score:.1f}/50")

    if score.static.issues:
        lines.append("")
        lines.append("Issues:")
        for issue in score.static.issues[:5]:  # Top 5 issues
            lines.append(f"  • {issue}")
        if len(score.static.issues) > 5:
            lines.append(f"  ... and {len(score.static.issues) - 5} more")

    lines.append("")
    lines.append("-" * 70)
    lines.append("PILLAR 2: SECURITY (50 points)")
    lines.append("-" * 70)
    lines.append(f"Score: {score.security.score:.1f}/50 (Grade {score.security.grade.value})")
    lines.append("")

    # Auto-reject flags
    if score.security.has_critical_high_conf:
        lines.append("🚨 CRITICAL finding (confidence >= 0.7) detected")
    if score.security.below_security_floor:
        lines.append(f"⚠️  Score below 50% floor ({score.security.score:.1f} < 25.0)")

    lines.append("")
    lines.append("Penalty Breakdown:")
    lines.append(f"  CRITICAL: -{score.security.critical_penalty:.1f}")
    lines.append(f"  HIGH:     -{score.security.high_penalty:.1f}")
    lines.append(f"  MEDIUM:   -{score.security.medium_penalty:.1f}")
    lines.append(f"  LOW:      -{score.security.low_penalty:.1f}")
    lines.append(f"  Total:    -{score.security.total_penalty:.1f}")
    lines.append(f"  Final:    {score.security.score:.1f}/50")

    lines.append("")
    lines.append(f"Findings Summary:")
    lines.append(f"  Scoreable (conf >= 0.5):  {len(score.security.scoreable_findings)}")
    lines.append(f"  Advisory (conf 0.3-0.5):   {len(score.security.advisory_findings)}")
    lines.append(f"  Hidden (conf < 0.3):       {len(score.security.hidden_findings)}")

    # Top findings
    if score.security.scoreable_findings:
        lines.append("")
        lines.append("Top Scoreable Findings:")
        for finding in score.security.scoreable_findings[:5]:
            lines.append(
                f"  [{finding.severity.value}] {finding.message} "
                f"(conf={finding.confidence:.2f}, penalty={finding.effective_penalty:.1f})"
            )
            if finding.file:
                lines.append(f"      File: {finding.file}")

    if score.security.advisory_findings:
        lines.append("")
        lines.append("Advisory Findings (not scored):")
        for finding in score.security.advisory_findings[:3]:
            lines.append(
                f"  [{finding.severity.value}] {finding.message} "
                f"(conf={finding.confidence:.2f})"
            )

    # OWASP ASI coverage
    if score.security.owasp_asi_coverage:
        lines.append("")
        lines.append("OWASP ASI Coverage:")
        for asi, count in sorted(score.security.owasp_asi_coverage.items()):
            lines.append(f"  {asi}: {count} finding(s)")

    lines.append("")
    lines.append("=" * 70)
    lines.append("RECOMMENDATION")
    lines.append("=" * 70)

    if score.publish_decision == PublishDecision.APPROVE:
        lines.append("✅ APPROVED - Ready to publish")
        if score.grade == Grade.A:
            lines.append("   Eligible for featured listing")
    elif score.publish_decision == PublishDecision.CONDITIONAL:
        lines.append("⚠️  CONDITIONAL - Publish with advisory")
        lines.append("   Users will see quality warnings")
    elif score.publish_decision == PublishDecision.REQUIRE_ACK:
        lines.append("⚠️  REQUIRES ACKNOWLEDGMENT")
        lines.append("   Author must explicitly confirm publish")
    else:  # BLOCK
        lines.append("🚫 BLOCKED - Cannot publish")
        if score.auto_reject:
            lines.append(f"   Reason: {score.auto_reject_reason}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)
