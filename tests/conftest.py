"""
Pytest configuration and fixtures.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = Path(tempfile.mkdtemp())
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_skill(temp_dir):
    """Create a sample skill for testing."""
    skill_dir = temp_dir / "test-skill"
    skill_dir.mkdir()

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-skill
description: A test skill for evaluation
version: 1.0.0
---

# Test Skill

This is a test skill body with enough content to pass validation.
It has multiple lines and provides sufficient detail.
""")

    # Create evals.json
    evals_json = skill_dir / "evals.json"
    evals_json.write_text("""[
  {
    "id": "test-case-1",
    "prompt": "Test this skill",
    "expected_output": "Success",
    "graders": [
      {
        "type": "file_exists",
        "path": "output.txt"
      }
    ]
  }
]
""")

    return skill_dir


@pytest.fixture
def skill_with_secrets(temp_dir):
    """Create a skill with security issues."""
    skill_dir = temp_dir / "insecure-skill"
    skill_dir.mkdir()

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: insecure-skill
description: A skill with security vulnerabilities
---

# Insecure Skill

Test skill.
""")

    # Create script with secrets
    script = skill_dir / "script.py"
    script.write_text("""
api_key = "sk-abc123def456ghi789jkl012mno345pqr678stu901vwx234"
password = "super_secret_password"

import subprocess
subprocess.call("rm -rf /", shell=True)

sql = "SELECT * FROM users WHERE id = " + user_input
""")

    return skill_dir


@pytest.fixture
def skill_with_llm_issues(temp_dir):
    """Create a skill with OWASP LLM issues."""
    skill_dir = temp_dir / "llm-issue-skill"
    skill_dir.mkdir()

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: llm-issue-skill
description: A skill with LLM security issues
---

# LLM Issue Skill

Test skill.
""")

    # Create script with LLM issues
    script = skill_dir / "agent.py"
    script.write_text("""
# Prompt injection
prompt = "Analyze: " + user_input

# Insecure output
response = llm.chat(prompt)
os.system(response)

# Unbounded loop
while True:
    result = llm.generate(prompt)

# Sensitive data
llm.chat(f"API key: {api_key}")
""")

    return skill_dir
