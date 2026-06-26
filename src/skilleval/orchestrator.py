"""
Main orchestrator for SkillEval evaluation pipeline.
"""

import time
from pathlib import Path

from skilleval.models import (
    Config,
    EvalResult,
    FinalReport,
    Grade,
)
from skilleval.utils.logger import logger
from skilleval.utils.skill_loader import load_skill
from skilleval.pillars.static_tests import StaticTestsPillar
from skilleval.pillars.security import SecurityPillar
from skilleval.pillars.harness import HarnessPillar


class Orchestrator:
    """Orchestrates the complete evaluation pipeline."""

    def __init__(self, config: Config):
        self.config = config

    def evaluate(self, skill_path: Path) -> EvalResult:
        """
        Run complete evaluation pipeline.

        Args:
            skill_path: Path to skill directory

        Returns:
            EvalResult with all pillar results and final report
        """
        start_time = time.time()

        logger.info(f"Starting evaluation of: {skill_path}")

        # Load skill
        skill = load_skill(skill_path)
        logger.info(f"Loaded skill: {skill.frontmatter.name}")

        result = EvalResult()

        # Pillar 1: Static Tests (20%)
        logger.info("Running Pillar 1: Static Tests...")
        static_pillar = StaticTestsPillar(self.config.static_tests)
        result.static_tests = static_pillar.run(skill_path)
        logger.info(f"Static Tests complete: {result.static_tests.score:.1f}/100 ({result.static_tests.grade.value})")

        # Pillar 2: Security (30%)
        logger.info("Running Pillar 2: Security...")
        security_pillar = SecurityPillar(self.config.security)
        result.security = security_pillar.run(skill_path)
        logger.info(f"Security complete: {result.security.score:.1f}/100 ({result.security.grade.value})")

        # Pillar 3: Harness (50%)
        logger.info("Running Pillar 3: Harness...")
        harness_pillar = HarnessPillar(self.config.harness)
        result.harness = harness_pillar.run(skill_path, skill.eval_cases)
        logger.info(f"Harness complete: {result.harness.score:.1f}/100 ({result.harness.grade.value})")

        # Calculate final score
        total_duration = time.time() - start_time

        result.final_report = self._generate_final_report(
            skill=skill,
            static_result=result.static_tests,
            security_result=result.security,
            harness_result=result.harness,
            duration=total_duration,
        )

        logger.info(f"Evaluation complete: {result.final_report.final_score:.1f}/100 ({result.final_report.grade.value})")

        return result

    def _generate_final_report(
        self,
        skill,
        static_result,
        security_result,
        harness_result,
        duration: float,
    ) -> FinalReport:
        """Generate final report with aggregated scores."""

        static_score = static_result.score if static_result else 0
        security_score = security_result.score if security_result else 0
        harness_score = harness_result.score if harness_result else 0

        # Calculate weighted final score
        weights = self.config.scoring.weights
        final_score = (
            static_score * weights["static_tests"]
            + security_score * weights["security"]
            + harness_score * weights["harness"]
        )

        # Determine grade
        if final_score >= 90:
            grade = Grade.A
        elif final_score >= 75:
            grade = Grade.B
        elif final_score >= 60:
            grade = Grade.C
        elif final_score >= 45:
            grade = Grade.D
        else:
            grade = Grade.F

        # Determine recommendation
        thresholds = self.config.scoring.thresholds

        if security_score < self.config.security.min_score:
            recommendation = "REJECT — Security score below threshold"
        elif final_score >= thresholds["approve"]:
            recommendation = "APPROVE — High quality skill"
        elif final_score >= thresholds["conditional"]:
            recommendation = "CONDITIONAL — Review warnings and improve"
        else:
            recommendation = "REJECT — Below quality threshold"

        # Build pillar scores with findings
        pillar_scores = {
            "static_tests": {
                "score": static_score,
                "grade": self._score_to_grade(static_score).value,
                "weight": weights["static_tests"],
            },
            "security": {
                "score": security_score,
                "grade": self._score_to_grade(security_score).value,
                "weight": weights["security"],
            },
            "harness": {
                "score": harness_score,
                "grade": self._score_to_grade(harness_score).value,
                "weight": weights["harness"],
            },
        }

        # Add detailed findings and scoring explanations
        if static_result:
            pillar_scores["static_tests"]["details"] = {
                "schema_valid": static_result.schema_valid,
                "structure_valid": static_result.structure_valid,
                "completeness": static_result.completeness,
                "issues": static_result.issues,
                "explanation": self._explain_static_score(static_result),
            }

        if security_result:
            pillar_scores["security"]["details"] = {
                "findings_total": security_result.findings_total,
                "by_severity": security_result.by_severity,
                "has_critical": security_result.has_critical,
                "has_high": security_result.has_high,
                "duration_seconds": security_result.duration_seconds,
                "explanation": self._explain_security_score(security_result),
            }
            pillar_scores["security"]["findings"] = [
                {
                    "type": f.type,
                    "severity": f.severity.value,
                    "message": f.message,
                    "file": f.file,
                    "line": f.line,
                    "remediation": f.remediation,
                }
                for f in security_result.findings
            ]

        if harness_result:
            pillar_scores["harness"]["details"] = {
                "functional_score": harness_result.functional_score,
                "safety_score": harness_result.safety_score,
                "functional_results": [
                    {
                        "case_id": fr.case_id,
                        "baseline_score": fr.baseline_score,
                        "skill_score": fr.skill_score,
                        "improvement": fr.improvement,
                        "improvement_pct": fr.improvement_pct,
                    }
                    for fr in harness_result.functional_results
                ],
                "safety_checks": [
                    {
                        "check": s.check,
                        "score": s.score,
                        "severity": s.severity.value,
                        "details": s.details,
                    }
                    for s in harness_result.safety_checks
                ],
                "explanation": self._explain_harness_score(harness_result),
            }

        # Generate overall explanation
        overall_explanation = self._explain_final_score(
            final_score, grade, recommendation,
            static_score, security_score, harness_score,
            weights, static_result, security_result, harness_result
        )

        return FinalReport(
            skill_name=skill.frontmatter.name,
            skill_version=skill.frontmatter.version,
            final_score=final_score,
            grade=grade,
            recommendation=recommendation,
            pillar_scores=pillar_scores,
            total_duration_seconds=duration,
            metadata={
                "skill_path": str(skill.path),
                "has_evals": skill.has_evals,
                "eval_cases_count": len(skill.eval_cases),
                "overall_explanation": overall_explanation,
            },
        )

    def _score_to_grade(self, score: float) -> Grade:
        """Convert numeric score to grade."""
        if score >= 90:
            return Grade.A
        elif score >= 75:
            return Grade.B
        elif score >= 60:
            return Grade.C
        elif score >= 45:
            return Grade.D
        else:
            return Grade.F

    def _explain_static_score(self, result) -> str:
        """Generate explanation for static test score."""
        explanations = []
        
        if result.score == 100.0:
            explanations.append("Perfect static validation - all checks passed.")
        else:
            if not result.schema_valid:
                explanations.append("SKILL.md schema validation failed.")
            if not result.structure_valid:
                explanations.append("Skill structure validation failed.")
            if result.completeness < 0.7:
                explanations.append(f"Low completeness score ({result.completeness:.1%}).")
            
            if result.issues:
                explanations.append(f"Found {len(result.issues)} issue(s):")
                for issue in result.issues[:5]:  # Top 5
                    explanations.append(f"  - {issue}")
                if len(result.issues) > 5:
                    explanations.append(f"  ... and {len(result.issues) - 5} more")
        
        return " ".join(explanations) if explanations else "No issues found."

    def _explain_security_score(self, result) -> str:
        """Generate detailed explanation for security score."""
        explanations = []
        
        if result.score == 100.0:
            explanations.append("Perfect security score - no vulnerabilities detected across all 6 frameworks (OWASP Web, OWASP LLM, OWASP Agentic, NIST AI RMF, ML Security, Custom Checks).")
        else:
            # Overall summary
            severity_weights = {
                "CRITICAL": 25,
                "HIGH": 10,
                "MEDIUM": 5,
                "LOW": 2,
                "INFO": 1,
            }
            
            total_deductions = 0
            severity_summary = []
            
            for sev, count in result.by_severity.items():
                weight = severity_weights.get(sev, 5)
                deduction = weight * count
                total_deductions += deduction
                severity_summary.append(f"{count} {sev} (-{deduction} points)")
            
            explanations.append(f"Security score: {result.score:.1f}/100. Deductions: {', '.join(severity_summary)}.")
            
            # Framework breakdown
            framework_counts = {}
            for finding in result.findings:
                if finding.type.startswith("LLM"):
                    fw = "OWASP LLM"
                elif finding.type.startswith("AGENT"):
                    fw = "OWASP Agentic"
                elif finding.type.startswith("NIST"):
                    fw = "NIST AI RMF"
                elif finding.type.startswith("MLSEC"):
                    fw = "ML Security"
                elif finding.type in ["SQL_INJECTION", "COMMAND_INJECTION", "XSS", "PATH_TRAVERSAL"]:
                    fw = "OWASP Web"
                else:
                    fw = "Custom Checks"
                
                framework_counts[fw] = framework_counts.get(fw, 0) + 1
            
            if framework_counts:
                fw_summary = [f"{fw}: {count}" for fw, count in framework_counts.items()]
                explanations.append(f"Findings by framework: {', '.join(fw_summary)}.")
            
            # Critical/High warnings
            if result.has_critical:
                critical_count = result.by_severity.get("CRITICAL", 0)
                explanations.append(f"⚠️ {critical_count} CRITICAL issue(s) require immediate attention.")
            
            if result.has_high:
                high_count = result.by_severity.get("HIGH", 0)
                explanations.append(f"⚠️ {high_count} HIGH severity issue(s) should be addressed before deployment.")
            
            # Top issues
            if result.findings:
                explanations.append(f"Top issues:")
                # Sort by severity
                severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
                sorted_findings = sorted(result.findings, key=lambda f: severity_order.get(f.severity.value, 5))
                
                for f in sorted_findings[:3]:  # Top 3
                    location = f"{f.file}:{f.line}" if f.line else f.file
                    explanations.append(f"  - [{f.severity.value}] {f.type}: {f.message} ({location})")
                
                if len(result.findings) > 3:
                    explanations.append(f"  ... and {len(result.findings) - 3} more (see findings list)")
        
        return " ".join(explanations)

    def _explain_harness_score(self, result) -> str:
        """Generate explanation for harness score."""
        explanations = []

        # Overall composition
        explanations.append(f"Harness score: {result.score:.1f}/100 = Functional ({result.functional_score:.1f}) + Safety ({result.safety_score:.1f}).")

        # Functional results
        if result.functional_results:
            # Count tests that showed improvement
            improved = sum(1 for fr in result.functional_results if fr.improvement > 0)
            total = len(result.functional_results)
            explanations.append(f"Functional tests: {improved}/{total} showed improvement.")

            failed_func = [fr for fr in result.functional_results if fr.skill_score < 70]
            if failed_func:
                explanations.append("Low-scoring tests:")
                for fr in failed_func[:3]:
                    explanations.append(f"  - {fr.case_id}: skill={fr.skill_score:.1f}, baseline={fr.baseline_score:.1f}")
                if len(failed_func) > 3:
                    explanations.append(f"  ... and {len(failed_func) - 3} more")

        # Safety checks
        if result.safety_checks:
            failed_safety = [s for s in result.safety_checks if s.score < 100]
            if failed_safety:
                explanations.append(f"Safety concerns:")
                for s in failed_safety[:3]:
                    explanations.append(f"  - {s.check} ({s.severity.value}): {s.details}")
                if len(failed_safety) > 3:
                    explanations.append(f"  ... and {len(failed_safety) - 3} more")
            else:
                explanations.append("All safety checks passed.")

        return " ".join(explanations)

    def _explain_final_score(self, final_score, grade, recommendation,
                            static_score, security_score, harness_score,
                            weights, static_result, security_result, harness_result) -> str:
        """Generate comprehensive explanation of final score."""
        lines = []
        
        lines.append(f"FINAL SCORE: {final_score:.1f}/100 (Grade: {grade.value})")
        lines.append(f"RECOMMENDATION: {recommendation}")
        lines.append("")
        
        lines.append("SCORE CALCULATION:")
        lines.append(f"  Final Score = (Static × {weights['static_tests']:.0%}) + (Security × {weights['security']:.0%}) + (Harness × {weights['harness']:.0%})")
        lines.append(f"  Final Score = ({static_score:.1f} × {weights['static_tests']:.0%}) + ({security_score:.1f} × {weights['security']:.0%}) + ({harness_score:.1f} × {weights['harness']:.0%})")
        lines.append(f"  Final Score = {static_score * weights['static_tests']:.1f} + {security_score * weights['security']:.1f} + {harness_score * weights['harness']:.1f}")
        lines.append(f"  Final Score = {final_score:.1f}")
        lines.append("")
        
        lines.append("PILLAR BREAKDOWN:")
        lines.append(f"  1. Static Tests: {static_score:.1f}/100 ({self._score_to_grade(static_score).value}) - Weight: {weights['static_tests']:.0%}")
        if static_result and static_result.issues:
            lines.append(f"     Issues: {', '.join(static_result.issues[:3])}")
        else:
            lines.append("     No issues found")
        
        lines.append(f"  2. Security: {security_score:.1f}/100 ({self._score_to_grade(security_score).value}) - Weight: {weights['security']:.0%}")
        if security_result and security_result.findings:
            lines.append(f"     Found {security_result.findings_total} finding(s) across 6 frameworks")
            for sev, count in security_result.by_severity.items():
                lines.append(f"       - {sev}: {count}")
        else:
            lines.append("     No security vulnerabilities found")
        
        lines.append(f"  3. Harness: {harness_score:.1f}/100 ({self._score_to_grade(harness_score).value}) - Weight: {weights['harness']:.0%}")
        if harness_result:
            lines.append(f"     Functional: {harness_result.functional_score:.1f}, Safety: {harness_result.safety_score:.1f}")
            if harness_result.functional_results:
                improved = sum(1 for fr in harness_result.functional_results if fr.improvement > 0)
                lines.append(f"     Tests: {improved}/{len(harness_result.functional_results)} showed improvement")
        
        lines.append("")
        lines.append("GRADE SCALE:")
        lines.append("  A: 90-100 (Excellent)")
        lines.append("  B: 75-89  (Good)")
        lines.append("  C: 60-74  (Acceptable)")
        lines.append("  D: 45-59  (Needs Improvement)")
        lines.append("  F: 0-44   (Fail)")
        
        return "\n".join(lines)
