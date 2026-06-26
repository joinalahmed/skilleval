"""
Pillar 4: Code Quality

Analyzes code quality, complexity, and maintainability.
"""

import time
from pathlib import Path
from typing import List

from skilleval.models import Finding, Severity, Grade
from skilleval.utils.complexity_analyzer import (
    calculate_complexity,
    assess_maintainability,
    ComplexityMetrics,
)
from skilleval.utils.logger import logger


class QualityResult:
    """Quality pillar result."""

    def __init__(
        self,
        score: float,
        grade: Grade,
        average_complexity: float,
        average_maintainability: float,
        total_loc: int,
        issues: List[Finding],
        duration_seconds: float,
    ):
        self.score = score
        self.grade = grade
        self.average_complexity = average_complexity
        self.average_maintainability = average_maintainability
        self.total_loc = total_loc
        self.issues = issues
        self.duration_seconds = duration_seconds


class QualityPillar:
    """Code quality evaluation pillar."""

    def __init__(self):
        pass

    def run(self, skill_path: Path) -> QualityResult:
        """
        Run quality analysis.

        Args:
            skill_path: Path to skill directory

        Returns:
            QualityResult
        """
        start_time = time.time()

        python_files = list(skill_path.rglob("*.py"))
        if not python_files:
            return self._empty_result(time.time() - start_time)

        all_metrics: List[ComplexityMetrics] = []
        issues: List[Finding] = []

        for file_path in python_files:
            try:
                metrics = calculate_complexity(file_path)
                all_metrics.append(metrics)

                # Assess file maintainability
                grade, file_issues = assess_maintainability(metrics)

                # Convert issues to findings
                for issue in file_issues:
                    severity = Severity.MEDIUM if grade in ["D", "F"] else Severity.LOW

                    issues.append(Finding(
                        type="QUALITY_ISSUE",
                        severity=severity,
                        message=issue,
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Refactor code to improve maintainability.",
                    ))

            except Exception as e:
                logger.warning(f"Could not analyze {file_path}: {e}")

        # Calculate averages
        if all_metrics:
            avg_complexity = sum(m.cyclomatic_complexity for m in all_metrics) / len(all_metrics)
            avg_maintainability = sum(m.maintainability_index for m in all_metrics) / len(all_metrics)
            total_loc = sum(m.lines_of_code for m in all_metrics)
        else:
            avg_complexity = 0
            avg_maintainability = 100
            total_loc = 0

        # Calculate quality score
        score = self._calculate_score(avg_complexity, avg_maintainability, issues)

        # Determine grade
        if score >= 90:
            grade = Grade.A
        elif score >= 75:
            grade = Grade.B
        elif score >= 60:
            grade = Grade.C
        elif score >= 45:
            grade = Grade.D
        else:
            grade = Grade.F

        duration = time.time() - start_time

        return QualityResult(
            score=score,
            grade=grade,
            average_complexity=avg_complexity,
            average_maintainability=avg_maintainability,
            total_loc=total_loc,
            issues=issues,
            duration_seconds=duration,
        )

    def _calculate_score(
        self,
        avg_complexity: float,
        avg_maintainability: float,
        issues: List[Finding],
    ) -> float:
        """Calculate overall quality score."""
        # Start with maintainability index
        score = avg_maintainability

        # Penalize high complexity
        if avg_complexity > 20:
            score -= 20
        elif avg_complexity > 10:
            score -= 10

        # Penalize issues
        for issue in issues:
            if issue.severity == Severity.HIGH:
                score -= 10
            elif issue.severity == Severity.MEDIUM:
                score -= 5
            else:
                score -= 2

        return max(0, min(100, score))

    def _empty_result(self, duration: float) -> QualityResult:
        """Return empty result when no Python files found."""
        return QualityResult(
            score=100.0,
            grade=Grade.A,
            average_complexity=0,
            average_maintainability=100,
            total_loc=0,
            issues=[],
            duration_seconds=duration,
        )
