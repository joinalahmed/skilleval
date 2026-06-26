"""
Tests for Harness pillar.
"""

import pytest
from pathlib import Path

from skilleval.pillars.harness import HarnessPillar
from skilleval.models import HarnessConfig, EvalCase, Grader


def test_harness_with_no_evals(sample_skill):
    """Test harness with no eval cases."""
    config = HarnessConfig()
    pillar = HarnessPillar(config)

    # Remove evals.json
    evals_file = sample_skill / "evals.json"
    if evals_file.exists():
        evals_file.unlink()

    result = pillar.run(sample_skill, [])

    assert result.score >= 0
    assert result.grade.value in ["A", "B", "C", "D", "F"]


def test_grader_file_exists():
    """Test file_exists grader."""
    from skilleval.pillars.harness import HarnessPillar
    import tempfile

    config = HarnessConfig()
    pillar = HarnessPillar(config)

    workspace = Path(tempfile.mkdtemp())
    test_file = workspace / "output.txt"
    test_file.write_text("test")

    grader = Grader(type="file_exists", path="output.txt")

    result = pillar._run_single_grader(grader, workspace)

    assert result.passed
    assert result.type == "file_exists"


def test_grader_json_schema():
    """Test json_schema grader."""
    from skilleval.pillars.harness import HarnessPillar
    import tempfile
    import json

    config = HarnessConfig()
    pillar = HarnessPillar(config)

    workspace = Path(tempfile.mkdtemp())
    test_file = workspace / "data.json"
    test_file.write_text(json.dumps({"key": "value"}))

    grader = Grader(type="json_schema", path="data.json")

    result = pillar._run_single_grader(grader, workspace)

    assert result.passed
    assert result.type == "json_schema"


def test_grader_content_match():
    """Test content_match grader."""
    from skilleval.pillars.harness import HarnessPillar
    import tempfile

    config = HarnessConfig()
    pillar = HarnessPillar(config)

    workspace = Path(tempfile.mkdtemp())
    test_file = workspace / "output.txt"
    test_file.write_text("Hello World")

    grader = Grader(type="content_match", path="output.txt", pattern="Hello")

    result = pillar._run_single_grader(grader, workspace)

    assert result.passed
    assert result.type == "content_match"


def test_grader_missing_file():
    """Test grader with missing file."""
    from skilleval.pillars.harness import HarnessPillar
    import tempfile

    config = HarnessConfig()
    pillar = HarnessPillar(config)

    workspace = Path(tempfile.mkdtemp())

    grader = Grader(type="file_exists", path="nonexistent.txt")

    result = pillar._run_single_grader(grader, workspace)

    assert not result.passed


def test_grader_score_calculation():
    """Test grader score calculation."""
    from skilleval.pillars.harness import HarnessPillar
    from skilleval.models import GraderResult

    config = HarnessConfig()
    pillar = HarnessPillar(config)

    results = [
        GraderResult(type="test1", passed=True, message="ok"),
        GraderResult(type="test2", passed=True, message="ok"),
        GraderResult(type="test3", passed=False, message="fail"),
    ]

    score = pillar._calculate_grader_score(results)

    assert score == pytest.approx(66.67, rel=0.1)


def test_functional_scoring():
    """Test functional result scoring."""
    config = HarnessConfig()
    pillar = HarnessPillar(config)

    eval_case = EvalCase(
        id="test",
        prompt="Test",
        expected_output="Output",
        graders=[Grader(type="file_exists", path="output.txt")],
    )

    baseline = {"workspace": Path("/tmp/baseline")}
    skill = {"workspace": Path("/tmp/skill")}

    result = pillar._compare_results(eval_case, baseline, skill)

    assert result.case_id == "test"
    assert result.baseline_score >= 0
    assert result.skill_score >= 0


def test_safety_checks_empty():
    """Test safety checks with no results."""
    config = HarnessConfig()
    pillar = HarnessPillar(config)

    checks = pillar._run_safety_checks(Path("/tmp"), [])

    assert isinstance(checks, list)
