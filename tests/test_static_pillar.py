"""
Tests for Static Tests pillar.
"""

import pytest
from pathlib import Path

from skilleval.pillars.static_tests import StaticTestsPillar
from skilleval.models import StaticTestsConfig


def test_valid_skill(sample_skill):
    """Test evaluation of a valid skill."""
    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    result = pillar.run(sample_skill)

    assert result.score == 100.0
    assert result.grade.value == "A"
    assert result.schema_valid
    assert result.structure_valid
    assert result.completeness >= 0.9
    assert len(result.issues) == 0


def test_missing_skill_md(temp_dir):
    """Test skill without SKILL.md."""
    skill_dir = temp_dir / "no-skill-md"
    skill_dir.mkdir()

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    with pytest.raises(Exception):
        pillar.run(skill_dir)


def test_invalid_frontmatter(temp_dir):
    """Test skill with invalid frontmatter."""
    skill_dir = temp_dir / "invalid-frontmatter"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: invalid name with spaces
description: short
---
Body
""")

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    result = pillar.run(skill_dir)
    assert result.score < 100.0


def test_description_too_long(temp_dir):
    """Test skill with description >500 chars."""
    skill_dir = temp_dir / "long-description"
    skill_dir.mkdir()

    long_desc = "a" * 501

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(f"""---
name: long-description
description: {long_desc}
---
Body content here.
""")

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    with pytest.raises(Exception):
        pillar.run(skill_dir)


def test_process_steps_detection(temp_dir):
    """Test detection of process steps in description."""
    skill_dir = temp_dir / "process-steps"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: process-steps
description: Exports data, generates reports, creates files, posts results
---
Body content here with sufficient length for validation.
""")

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    result = pillar.run(skill_dir)
    assert any("process steps" in issue.lower() for issue in result.issues)


def test_missing_evals(temp_dir):
    """Test skill without evals.json."""
    skill_dir = temp_dir / "no-evals"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: no-evals
description: A skill without evals for testing
---
Body content here.
""")

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    result = pillar.run(skill_dir)
    # Should still pass but with reduced score
    assert result.score < 100.0


def test_short_body(temp_dir):
    """Test skill with short body."""
    skill_dir = temp_dir / "short-body"
    skill_dir.mkdir()

    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: short-body
description: A test skill with a short body
---
Short.
""")

    config = StaticTestsConfig()
    pillar = StaticTestsPillar(config)

    result = pillar.run(skill_dir)
    assert result.score < 100.0
    assert result.completeness < 1.0
