"""
Pillar 1: Static Tests

Validates skill structure and quality before execution.
"""

import time
import re
from pathlib import Path

from skilleval.models import (
    StaticTestsConfig,
    StaticTestResult,
    Grade,
)
from skilleval.utils.skill_loader import load_skill
from skilleval.utils.logger import logger


class StaticTestsPillar:
    """Static tests evaluation pillar."""

    def __init__(self, config: StaticTestsConfig):
        self.config = config

    def run(self, skill_path: Path) -> StaticTestResult:
        """
        Run static tests on a skill.

        Args:
            skill_path: Path to skill directory

        Returns:
            StaticTestResult
        """
        start_time = time.time()

        try:
            skill = load_skill(skill_path)
        except Exception as e:
            logger.error(f"Failed to load skill: {e}")
            return StaticTestResult(
                score=0,
                grade=Grade.F,
                schema_valid=False,
                structure_valid=False,
                completeness=0.0,
                issues=[f"Failed to load skill: {e}"],
                duration_seconds=time.time() - start_time,
            )

        issues = []
        schema_valid = True
        structure_valid = True
        completeness = 1.0

        # Check schema
        try:
            # Frontmatter was already validated during load
            pass
        except Exception as e:
            schema_valid = False
            issues.append(f"Schema validation failed: {e}")

        # Check structure
        if not skill.has_evals:
            completeness -= 0.3
            issues.append("No evals/evals.json - harness testing will be skipped")

        # Check description quality
        desc_length = len(skill.frontmatter.description)
        if desc_length < self.config.min_description_length:
            completeness -= 0.05
            issues.append(f"Description very short ({desc_length} < {self.config.min_description_length} chars)")

        # Check body length
        body_length = len(skill.body)
        if body_length < self.config.min_body_length:
            completeness -= 0.1
            issues.append(f"SKILL.md body very short ({body_length} < {self.config.min_body_length} chars)")

        # Check for process steps in description
        if self.config.check_description_steps:
            if self._description_has_process_steps(skill.frontmatter.description):
                completeness -= 0.1
                issues.append(
                    "WARNING: Description contains process steps. "
                    "This may cause the model to follow description instead of body. "
                    "Use high-level intent only."
                )

        # Calculate score
        score = 100.0

        if not schema_valid:
            score -= 50

        if not structure_valid:
            score -= 30

        # Completeness penalties
        score -= (1.0 - completeness) * 20

        score = max(0, min(100, score))

        # Determine grade
        if score >= 90:
            grade = Grade.A
        elif score >= 80:
            grade = Grade.B
        elif score >= 70:
            grade = Grade.C
        elif score >= 60:
            grade = Grade.D
        else:
            grade = Grade.F

        duration = time.time() - start_time

        return StaticTestResult(
            score=score,
            grade=grade,
            schema_valid=schema_valid,
            structure_valid=structure_valid,
            completeness=completeness,
            issues=issues,
            duration_seconds=duration,
        )

    def _description_has_process_steps(self, description: str) -> bool:
        """
        Detect if description has action verbs indicating process steps.

        Based on skill-conductor insight: descriptions with process steps
        cause the model to follow the description and skip the body.
        """
        description_lower = description.lower()

        # Action verbs that indicate process steps
        action_verbs = [
            "exports", "generates", "creates", "posts", "sends",
            "fetches", "downloads", "uploads", "processes", "transforms",
            "executes", "runs", "builds", "compiles", "deploys",
        ]

        # Count action verbs
        count = sum(1 for verb in action_verbs if verb in description_lower)

        # If 3+ action verbs, likely listing steps
        return count >= 3
