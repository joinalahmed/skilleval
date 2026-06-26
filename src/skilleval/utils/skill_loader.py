"""
Skill loading utilities.
"""

import json
import re
from pathlib import Path
from typing import Dict, Any

import yaml

from skilleval.models import Skill, SkillFrontmatter, EvalCase, Grader
from skilleval.utils.logger import logger


def load_skill(skill_path: Path) -> Skill:
    """
    Load a skill from a directory.

    Args:
        skill_path: Path to skill directory

    Returns:
        Skill object

    Raises:
        ValueError: If SKILL.md doesn't exist or is invalid
    """
    skill_path = Path(skill_path)

    if not skill_path.is_dir():
        raise ValueError(f"Skill path is not a directory: {skill_path}")

    # Load SKILL.md
    skill_md_path = skill_path / "SKILL.md"
    if not skill_md_path.exists():
        raise ValueError(f"SKILL.md not found in {skill_path}")

    skill_md = skill_md_path.read_text()

    # Parse frontmatter and body
    frontmatter_dict, body = parse_skill_md(skill_md)

    # Validate frontmatter
    try:
        frontmatter = SkillFrontmatter(**frontmatter_dict)
    except Exception as e:
        raise ValueError(f"Invalid SKILL.md frontmatter: {e}")

    # Load eval cases if present
    eval_cases = []
    has_evals = False

    evals_path = skill_path / "evals" / "evals.json"
    if evals_path.exists():
        has_evals = True
        try:
            with open(evals_path) as f:
                evals_data = json.load(f)

            for eval_dict in evals_data.get("evals", []):
                # Convert graders
                graders = []
                for grader_dict in eval_dict.get("graders", []):
                    graders.append(Grader(**grader_dict))

                eval_case = EvalCase(
                    id=eval_dict["id"],
                    prompt=eval_dict["prompt"],
                    expected_output=eval_dict["expected_output"],
                    files=eval_dict.get("files", []),
                    graders=graders,
                    assertions=eval_dict.get("assertions", []),
                )
                eval_cases.append(eval_case)

        except Exception as e:
            logger.warning(f"Failed to load evals.json: {e}")

    # Check for other directories
    has_scripts = (skill_path / "scripts").exists()
    has_references = (skill_path / "references").exists()
    has_agents = (skill_path / "agents").exists()

    return Skill(
        path=skill_path,
        frontmatter=frontmatter,
        body=body,
        eval_cases=eval_cases,
        has_evals=has_evals,
        has_scripts=has_scripts,
        has_references=has_references,
        has_agents=has_agents,
    )


def parse_skill_md(content: str) -> tuple[Dict[str, Any], str]:
    """
    Parse SKILL.md frontmatter and body.

    Args:
        content: SKILL.md file content

    Returns:
        Tuple of (frontmatter_dict, body)
    """
    # Match YAML frontmatter between --- delimiters
    frontmatter_pattern = r"^---\s*\n(.*?)\n---\s*\n(.*)$"
    match = re.match(frontmatter_pattern, content, re.DOTALL)

    if not match:
        raise ValueError("SKILL.md missing frontmatter (--- delimiters)")

    frontmatter_yaml = match.group(1)
    body = match.group(2).strip()

    # Parse YAML
    try:
        frontmatter_dict = yaml.safe_load(frontmatter_yaml)
    except Exception as e:
        raise ValueError(f"Failed to parse frontmatter YAML: {e}")

    if not isinstance(frontmatter_dict, dict):
        raise ValueError("Frontmatter must be a YAML object")

    return frontmatter_dict, body
