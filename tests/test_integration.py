"""
Integration tests for complete evaluation pipeline.
"""

import pytest
from pathlib import Path

from skilleval.orchestrator import Orchestrator
from skilleval.models import Config


def test_full_evaluation(sample_skill):
    """Test complete evaluation pipeline."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(sample_skill)

    assert result.static_tests is not None
    assert result.security is not None
    assert result.harness is not None
    assert result.final_report is not None

    # Check final report
    assert result.final_report.final_score >= 0
    assert result.final_report.final_score <= 100
    assert result.final_report.grade.value in ["A", "B", "C", "D", "F"]


def test_evaluation_with_issues(skill_with_secrets):
    """Test evaluation of skill with security issues."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(skill_with_secrets)

    # Should detect security issues
    assert result.security.findings_total > 0
    assert result.final_report.final_score < 100


def test_evaluation_deterministic(sample_skill):
    """Test that evaluation is deterministic."""
    config = Config()
    orchestrator = Orchestrator(config)

    result1 = orchestrator.evaluate(sample_skill)
    result2 = orchestrator.evaluate(sample_skill)

    # Scores should be identical
    assert result1.final_report.final_score == result2.final_report.final_score
    assert result1.static_tests.score == result2.static_tests.score
    assert result1.security.score == result2.security.score


def test_weighted_scoring(sample_skill):
    """Test weighted score calculation."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(sample_skill)

    # Calculate expected weighted score
    weights = config.scoring.weights
    expected = (
        result.static_tests.score * weights["static_tests"]
        + result.security.score * weights["security"]
        + result.harness.score * weights["harness"]
    )

    assert abs(result.final_report.final_score - expected) < 0.01


def test_grade_assignment(temp_dir):
    """Test grade assignment thresholds."""
    # This would require creating skills with specific scores
    # For now, just verify grades are assigned
    config = Config()
    orchestrator = Orchestrator(config)

    # Use sample skill (should get B or higher)
    skill_dir = temp_dir / "grade-test"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: grade-test
description: Test skill for grade assignment verification
---
Body content.
""")

    result = orchestrator.evaluate(skill_dir)
    assert result.final_report.grade.value in ["A", "B", "C", "D", "F"]


def test_recommendation_logic(skill_with_secrets):
    """Test recommendation logic."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(skill_with_secrets)

    # With security issues, should get REJECT or CONDITIONAL
    assert "REJECT" in result.final_report.recommendation or \
           "CONDITIONAL" in result.final_report.recommendation


def test_report_structure(sample_skill):
    """Test final report structure."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(sample_skill)
    report = result.final_report

    # Check required fields
    assert report.skill_name
    assert report.framework_version
    assert report.final_score >= 0
    assert report.grade
    assert report.recommendation
    assert report.pillar_scores
    assert report.total_duration_seconds >= 0
    assert report.deterministic is True
    assert report.run_to_run_variance == "0%"


def test_pillar_breakdown(sample_skill):
    """Test pillar score breakdown."""
    config = Config()
    orchestrator = Orchestrator(config)

    result = orchestrator.evaluate(sample_skill)

    pillar_scores = result.final_report.pillar_scores

    assert "static_tests" in pillar_scores
    assert "security" in pillar_scores
    assert "harness" in pillar_scores

    for pillar, data in pillar_scores.items():
        assert "score" in data
        assert "grade" in data
        assert "weight" in data
