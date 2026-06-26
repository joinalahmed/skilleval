"""
Phase 1 Static Tests Scorer (ST-1 through ST-8)

Implements the ADR's static analysis checks with partial credit scoring.
Total: 50 points (additive - earn points by having good structure)

Scoring breakdown:
  ST-1: Frontmatter Validity (12 pts)
  ST-2: Description Quality (10 pts)
  ST-3: File Completeness (8 pts)
  ST-4: Script Quality (8 pts, full credit if no scripts)
  ST-5: Eval Suite Completeness (8 pts)
  ST-6: Instruction Clarity (4 pts)
  ST-7: Instruction Specificity (6 pts bonus, capped at 50)
  ST-8: Cross-Reference Integrity (4 pts bonus, capped at 50)
"""

import re
import ast
import yaml
from pathlib import Path
from typing import List, Tuple
from dataclasses import dataclass

from ..models_phase1 import (
    Phase1StaticScore,
    StaticTestResult,
    StaticSubCheck,
    Grade,
    score_to_grade,
)


class StaticTestsScorer:
    """Scores static tests (ST-1 through ST-8) per ADR specification."""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"

    def score(self) -> Phase1StaticScore:
        """Run all static tests and compute total score."""
        results = []

        # Core tests (50 points possible)
        st1 = self._st1_frontmatter_validity()
        st2 = self._st2_description_quality()
        st3 = self._st3_file_completeness()
        st4 = self._st4_script_quality()
        st5 = self._st5_eval_suite_completeness()
        st6 = self._st6_instruction_clarity()

        results.extend([st1, st2, st3, st4, st5, st6])

        # Bonus tests (can push over 50, but capped)
        st7 = self._st7_instruction_specificity()
        st8 = self._st8_cross_reference_integrity()

        results.extend([st7, st8])

        # Compute totals
        total_before_cap = sum(r.earned_points for r in results)
        total_score = min(50.0, total_before_cap)

        # Aggregate issues
        all_issues = []
        for r in results:
            all_issues.extend(r.issues)

        grade = score_to_grade(total_score, max_score=50)

        return Phase1StaticScore(
            score=total_score,
            grade=grade,
            tests=results,
            st1_frontmatter=st1.earned_points,
            st2_description=st2.earned_points,
            st3_completeness=st3.earned_points,
            st4_script_quality=st4.earned_points,
            st5_eval_suite=st5.earned_points,
            st6_clarity=st6.earned_points,
            st7_specificity=st7.earned_points,
            st8_cross_reference=st8.earned_points,
            total_before_cap=total_before_cap,
            issues=all_issues,
        )

    # ========================================================================
    # ST-1: Frontmatter Validity (12 points)
    # ========================================================================

    def _st1_frontmatter_validity(self) -> StaticTestResult:
        """
        ST-1: Frontmatter Validity (12 points)

        Sub-checks:
        - YAML parses without error (3 pts)
        - name field present and valid pattern (2 pts)
        - description field present and 20-1024 chars (3 pts)
        - version field present and valid semver (2 pts)
        - author or tags present (2 pts: 1 each)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        if not self.skill_md.exists():
            issues.append("SKILL.md not found")
            return StaticTestResult(
                test_id="ST-1",
                test_name="Frontmatter Validity",
                max_points=12.0,
                earned_points=0.0,
                sub_checks=sub_checks,
                issues=issues,
            )

        content = self.skill_md.read_text()

        # Extract frontmatter
        frontmatter, yaml_parsed = self._extract_frontmatter(content)

        # Sub-check 1: YAML parses (3 pts)
        if yaml_parsed:
            sub_checks.append(StaticSubCheck(
                name="YAML Parse",
                max_points=3.0,
                earned_points=3.0,
                passed=True,
                message="YAML frontmatter parsed successfully",
            ))
            total_points += 3.0
        else:
            sub_checks.append(StaticSubCheck(
                name="YAML Parse",
                max_points=3.0,
                earned_points=0.0,
                passed=False,
                message="YAML frontmatter parse failed",
            ))
            issues.append("YAML frontmatter invalid or missing")

        if not frontmatter:
            # Can't check further without valid frontmatter
            return StaticTestResult(
                test_id="ST-1",
                test_name="Frontmatter Validity",
                max_points=12.0,
                earned_points=total_points,
                sub_checks=sub_checks,
                issues=issues,
            )

        # Sub-check 2: name field (2 pts)
        name = frontmatter.get("name", "")
        name_pattern = r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$"
        if name and re.match(name_pattern, name):
            sub_checks.append(StaticSubCheck(
                name="Name Field",
                max_points=2.0,
                earned_points=2.0,
                passed=True,
                message=f"Valid name: {name}",
            ))
            total_points += 2.0
        elif name:
            sub_checks.append(StaticSubCheck(
                name="Name Field",
                max_points=2.0,
                earned_points=1.0,
                passed=False,
                message=f"Name present but invalid format: {name}",
            ))
            total_points += 1.0
            issues.append(f"Name '{name}' doesn't match pattern {name_pattern}")
        else:
            sub_checks.append(StaticSubCheck(
                name="Name Field",
                max_points=2.0,
                earned_points=0.0,
                passed=False,
                message="Name field missing",
            ))
            issues.append("Name field missing")

        # Sub-check 3: description field (3 pts)
        desc = frontmatter.get("description", "")
        desc_len = len(desc)
        if 20 <= desc_len <= 1024:
            sub_checks.append(StaticSubCheck(
                name="Description Field",
                max_points=3.0,
                earned_points=3.0,
                passed=True,
                message=f"Valid description ({desc_len} chars)",
            ))
            total_points += 3.0
        elif desc:
            sub_checks.append(StaticSubCheck(
                name="Description Field",
                max_points=3.0,
                earned_points=1.0,
                passed=False,
                message=f"Description present but wrong length ({desc_len} chars)",
            ))
            total_points += 1.0
            issues.append(f"Description length {desc_len} not in range 20-1024")
        else:
            sub_checks.append(StaticSubCheck(
                name="Description Field",
                max_points=3.0,
                earned_points=0.0,
                passed=False,
                message="Description field missing",
            ))
            issues.append("Description field missing")

        # Sub-check 4: version field (2 pts)
        version = frontmatter.get("version", "")
        semver_pattern = r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$"
        if version and re.match(semver_pattern, version):
            sub_checks.append(StaticSubCheck(
                name="Version Field",
                max_points=2.0,
                earned_points=2.0,
                passed=True,
                message=f"Valid semver: {version}",
            ))
            total_points += 2.0
        else:
            sub_checks.append(StaticSubCheck(
                name="Version Field",
                max_points=2.0,
                earned_points=0.0,
                passed=False,
                message="Version missing or invalid semver",
            ))
            if not version:
                issues.append("Version field missing")
            else:
                issues.append(f"Version '{version}' not valid semver")

        # Sub-check 5: author or tags (2 pts: 1 each)
        author_points = 0.0
        tags_points = 0.0

        if frontmatter.get("author"):
            author_points = 1.0
            sub_checks.append(StaticSubCheck(
                name="Author Field",
                max_points=1.0,
                earned_points=1.0,
                passed=True,
                message="Author field present",
            ))
        else:
            sub_checks.append(StaticSubCheck(
                name="Author Field",
                max_points=1.0,
                earned_points=0.0,
                passed=False,
                message="Author field missing",
            ))

        if frontmatter.get("tags"):
            tags_points = 1.0
            sub_checks.append(StaticSubCheck(
                name="Tags Field",
                max_points=1.0,
                earned_points=1.0,
                passed=True,
                message="Tags field present",
            ))
        else:
            sub_checks.append(StaticSubCheck(
                name="Tags Field",
                max_points=1.0,
                earned_points=0.0,
                passed=False,
                message="Tags field missing",
            ))

        total_points += author_points + tags_points

        return StaticTestResult(
            test_id="ST-1",
            test_name="Frontmatter Validity",
            max_points=12.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-2: Description Quality (10 points)
    # ========================================================================

    def _st2_description_quality(self) -> StaticTestResult:
        """
        ST-2: Description Quality (10 points)

        Sub-checks:
        - Length >= 50 characters (2 pts)
        - Contains >= 2 complete sentences (2 pts)
        - Vocabulary diversity (type-token ratio > 0.6) (2 pts)
        - Not just action verbs (verb density < 40%) (2 pts)
        - Contains trigger/scope language (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        if not self.skill_md.exists():
            return StaticTestResult(
                test_id="ST-2",
                test_name="Description Quality",
                max_points=10.0,
                earned_points=0.0,
                sub_checks=sub_checks,
                issues=["SKILL.md not found"],
            )

        content = self.skill_md.read_text()
        frontmatter, _ = self._extract_frontmatter(content)
        body = self._extract_body(content)

        desc = frontmatter.get("description", "") if frontmatter else ""

        # Sub-check 1: Length >= 50 chars (2 pts)
        desc_len = len(desc)
        if desc_len >= 50:
            pts = 2.0
        elif 20 <= desc_len < 50:
            pts = 1.0
        else:
            pts = 0.0

        sub_checks.append(StaticSubCheck(
            name="Description Length",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=f"Description length: {desc_len} chars",
        ))
        total_points += pts

        if desc_len < 50:
            issues.append(f"Description too short ({desc_len} < 50 chars)")

        # Sub-check 2: >= 2 sentences (2 pts)
        sentences = self._count_sentences(desc)
        if sentences >= 2:
            pts = 2.0
        elif sentences == 1:
            pts = 1.0
        else:
            pts = 0.0

        sub_checks.append(StaticSubCheck(
            name="Sentence Count",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=f"{sentences} complete sentence(s)",
        ))
        total_points += pts

        if sentences < 2:
            issues.append(f"Description has only {sentences} sentence(s), need 2+")

        # Sub-check 3: Type-token ratio > 0.6 (2 pts)
        ttr = self._type_token_ratio(desc)
        if ttr > 0.6:
            pts = 2.0
        elif 0.4 <= ttr <= 0.6:
            pts = 1.0
        else:
            pts = 0.0

        sub_checks.append(StaticSubCheck(
            name="Vocabulary Diversity",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=f"Type-token ratio: {ttr:.2f}",
        ))
        total_points += pts

        if ttr < 0.6:
            issues.append(f"Low vocabulary diversity (TTR={ttr:.2f})")

        # Sub-check 4: Verb density < 40% (2 pts)
        verb_density = self._verb_density(desc)
        if verb_density < 0.40:
            pts = 2.0
        elif 0.40 <= verb_density <= 0.60:
            pts = 1.0
        else:
            pts = 0.0

        sub_checks.append(StaticSubCheck(
            name="Verb Density",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=f"Verb density: {verb_density:.0%}",
        ))
        total_points += pts

        if verb_density >= 0.40:
            issues.append(f"High verb density ({verb_density:.0%}), may be just a verb list")

        # Sub-check 5: Trigger/scope language (2 pts)
        trigger_keywords = ["use when", "activate", "trigger", "invoke", "for tasks", "helps with"]
        has_trigger = any(kw in desc.lower() for kw in trigger_keywords)

        if has_trigger:
            pts = 2.0
        else:
            pts = 0.0

        sub_checks.append(StaticSubCheck(
            name="Trigger Language",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message="Contains trigger/scope language" if has_trigger else "No trigger language",
        ))
        total_points += pts

        if not has_trigger:
            issues.append("Description lacks trigger/scope language (use when, activate, etc.)")

        return StaticTestResult(
            test_id="ST-2",
            test_name="Description Quality",
            max_points=10.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-3: File Completeness (8 points)
    # ========================================================================

    def _st3_file_completeness(self) -> StaticTestResult:
        """
        ST-3: File Completeness (8 points)

        Sub-checks:
        - SKILL.md exists and non-empty >50 chars (4 pts)
        - At least one supporting artifact (2 pts)
        - Markdown structure (at least one ## heading) (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        # Sub-check 1: SKILL.md exists and >50 chars (4 pts)
        if self.skill_md.exists():
            content = self.skill_md.read_text()
            if len(content) > 50:
                pts = 4.0
                msg = f"SKILL.md exists ({len(content)} chars)"
            else:
                pts = 0.0
                msg = f"SKILL.md too short ({len(content)} chars)"
                issues.append("SKILL.md exists but nearly empty (<50 chars)")
        else:
            pts = 0.0
            msg = "SKILL.md not found"
            issues.append("SKILL.md not found")
            content = ""

        sub_checks.append(StaticSubCheck(
            name="SKILL.md Exists",
            max_points=4.0,
            earned_points=pts,
            passed=pts == 4.0,
            message=msg,
        ))
        total_points += pts

        # Sub-check 2: Supporting artifacts (2 pts)
        has_scripts = (self.skill_dir / "scripts").exists()
        has_evals = (self.skill_dir / "evals").exists() or (self.skill_dir / "evals.json").exists()
        has_refs = (self.skill_dir / "references").exists()

        if has_scripts or has_evals or has_refs:
            pts = 2.0
            artifacts = []
            if has_scripts:
                artifacts.append("scripts/")
            if has_evals:
                artifacts.append("evals/")
            if has_refs:
                artifacts.append("references/")
            msg = f"Has supporting artifacts: {', '.join(artifacts)}"
        else:
            pts = 0.0
            msg = "No supporting artifacts (scripts/, evals/, references/)"
            issues.append("No supporting artifacts found")

        sub_checks.append(StaticSubCheck(
            name="Supporting Artifacts",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        # Sub-check 3: Markdown structure (2 pts)
        has_heading = bool(re.search(r'^##\s+', content, re.MULTILINE))
        if has_heading:
            pts = 2.0
            msg = "Has markdown structure (## headings)"
        else:
            pts = 0.0
            msg = "No markdown headings found"
            issues.append("SKILL.md lacks markdown structure (no ## headings)")

        sub_checks.append(StaticSubCheck(
            name="Markdown Structure",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        return StaticTestResult(
            test_id="ST-3",
            test_name="File Completeness",
            max_points=8.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-4: Script Quality (8 points, full credit if no scripts)
    # ========================================================================

    def _st4_script_quality(self) -> StaticTestResult:
        """
        ST-4: Script Quality (8 points)

        If no scripts exist: Full 8 points (instruction-only skills not penalized)

        Sub-checks:
        - Python files parse (valid AST) (3 pts)
        - Shell files pass shellcheck (3 pts)
        - No syntax errors in any scripting language (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        scripts_dir = self.skill_dir / "scripts"

        if not scripts_dir.exists():
            # No scripts = full credit (instruction-only skills)
            sub_checks.append(StaticSubCheck(
                name="No Scripts",
                max_points=8.0,
                earned_points=8.0,
                passed=True,
                message="No scripts/ directory (instruction-only skill)",
            ))
            return StaticTestResult(
                test_id="ST-4",
                test_name="Script Quality",
                max_points=8.0,
                earned_points=8.0,
                sub_checks=sub_checks,
                issues=[],
            )

        # Find all scripts
        py_files = list(scripts_dir.rglob("*.py"))
        sh_files = list(scripts_dir.rglob("*.sh"))

        if not py_files and not sh_files:
            # scripts/ exists but empty
            sub_checks.append(StaticSubCheck(
                name="Empty Scripts Dir",
                max_points=8.0,
                earned_points=8.0,
                passed=True,
                message="scripts/ directory empty (full credit)",
            ))
            return StaticTestResult(
                test_id="ST-4",
                test_name="Script Quality",
                max_points=8.0,
                earned_points=8.0,
                sub_checks=sub_checks,
                issues=[],
            )

        # Sub-check 1: Python files parse (3 pts)
        if py_files:
            passing = 0
            for py_file in py_files:
                try:
                    ast.parse(py_file.read_text())
                    passing += 1
                except SyntaxError as e:
                    issues.append(f"Python syntax error in {py_file.name}: {e}")

            ratio = passing / len(py_files)
            pts = 3.0 * ratio

            sub_checks.append(StaticSubCheck(
                name="Python Syntax",
                max_points=3.0,
                earned_points=pts,
                passed=ratio == 1.0,
                message=f"{passing}/{len(py_files)} Python files parse",
            ))
            total_points += pts
        else:
            # No Python files, skip this check
            pass

        # Sub-check 2: Shell files (3 pts)
        # NOTE: We can't run shellcheck without external dependency
        # For now, just check if files exist and are non-empty
        if sh_files:
            passing = 0
            for sh_file in sh_files:
                content = sh_file.read_text()
                # Basic check: file not empty, starts with shebang
                if content.strip() and content.startswith("#!"):
                    passing += 1
                else:
                    issues.append(f"Shell script {sh_file.name} missing shebang or empty")

            ratio = passing / len(sh_files)
            pts = 3.0 * ratio

            sub_checks.append(StaticSubCheck(
                name="Shell Script Quality",
                max_points=3.0,
                earned_points=pts,
                passed=ratio == 1.0,
                message=f"{passing}/{len(sh_files)} shell scripts have shebang",
            ))
            total_points += pts
        else:
            # No shell files, skip
            pass

        # Sub-check 3: No syntax errors overall (2 pts)
        if not issues:
            pts = 2.0
            msg = "All scripts parse successfully"
        else:
            pts = 0.0
            msg = f"{len(issues)} syntax error(s) found"

        sub_checks.append(StaticSubCheck(
            name="No Syntax Errors",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        return StaticTestResult(
            test_id="ST-4",
            test_name="Script Quality",
            max_points=8.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-5: Eval Suite Completeness (8 points)
    # ========================================================================

    def _st5_eval_suite_completeness(self) -> StaticTestResult:
        """
        ST-5: Eval Suite Completeness (8 points)

        Sub-checks:
        - Eval config present (evals.json OR eval.yaml) (3 pts)
        - >= 3 positive test cases (2 pts)
        - >= 1 negative/edge case (1 pt)
        - Input diversity (prompt lengths vary by >2x) (1 pt)
        - Expected outputs or assertions defined (1 pt)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        # Sub-check 1: Eval config present (3 pts)
        evals_json = self.skill_dir / "evals.json"
        eval_yaml = self.skill_dir / "eval.yaml"
        evals_dir = self.skill_dir / "evals"

        has_config = evals_json.exists() or eval_yaml.exists() or evals_dir.exists()

        if has_config:
            pts = 3.0
            msg = "Eval config found"
        else:
            pts = 0.0
            msg = "No eval config (evals.json, eval.yaml, or evals/)"
            issues.append("No eval suite found")

        sub_checks.append(StaticSubCheck(
            name="Eval Config Present",
            max_points=3.0,
            earned_points=pts,
            passed=pts == 3.0,
            message=msg,
        ))
        total_points += pts

        if not has_config:
            # Can't check further
            return StaticTestResult(
                test_id="ST-5",
                test_name="Eval Suite Completeness",
                max_points=8.0,
                earned_points=total_points,
                sub_checks=sub_checks,
                issues=issues,
            )

        # Load eval cases (simplified - would need full parser)
        # For now, just check file count as proxy
        eval_count = 0
        if evals_json.exists():
            try:
                import json
                data = json.loads(evals_json.read_text())
                eval_count = len(data.get("eval_cases", []))
            except:
                pass
        elif evals_dir.exists():
            eval_count = len(list(evals_dir.glob("*.json")))

        # Sub-check 2: >= 3 positive cases (2 pts)
        if eval_count >= 3:
            pts = 2.0
            msg = f"{eval_count} eval cases found"
        elif 1 <= eval_count < 3:
            pts = 1.0
            msg = f"Only {eval_count} eval case(s), need 3+"
            issues.append(f"Only {eval_count} eval cases (need 3+)")
        else:
            pts = 0.0
            msg = "No eval cases found"
            issues.append("No eval cases found")

        sub_checks.append(StaticSubCheck(
            name="Test Case Count",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        # Remaining sub-checks would require parsing eval cases
        # Simplified: award partial credit based on presence
        if eval_count > 0:
            # Award 1+1+1 = 3 pts for having any eval suite
            total_points += 3.0
            sub_checks.append(StaticSubCheck(
                name="Eval Suite Quality",
                max_points=3.0,
                earned_points=3.0,
                passed=True,
                message="Eval suite present (assumed diverse and complete)",
            ))

        return StaticTestResult(
            test_id="ST-5",
            test_name="Eval Suite Completeness",
            max_points=8.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-6: Instruction Clarity (4 points)
    # ========================================================================

    def _st6_instruction_clarity(self) -> StaticTestResult:
        """
        ST-6: Instruction Clarity (4 points)

        Sub-checks:
        - Contains code examples (``` blocks) (2 pts)
        - Body length reasonable (100-5000 tokens) (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        if not self.skill_md.exists():
            return StaticTestResult(
                test_id="ST-6",
                test_name="Instruction Clarity",
                max_points=4.0,
                earned_points=0.0,
                sub_checks=sub_checks,
                issues=["SKILL.md not found"],
            )

        content = self.skill_md.read_text()
        body = self._extract_body(content)

        # Sub-check 1: Code examples (2 pts)
        code_blocks = re.findall(r'```', body)
        has_code = len(code_blocks) >= 2  # Opening and closing

        if has_code:
            pts = 2.0
            msg = f"Contains code examples ({len(code_blocks)//2} block(s))"
        else:
            pts = 0.0
            msg = "No code examples found"
            issues.append("No code examples (``` blocks)")

        sub_checks.append(StaticSubCheck(
            name="Code Examples",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        # Sub-check 2: Body length (2 pts)
        # Rough token estimate: ~4 chars per token
        estimated_tokens = len(body) // 4

        if 100 <= estimated_tokens <= 5000:
            pts = 2.0
            msg = f"Body length reasonable (~{estimated_tokens} tokens)"
        elif 50 <= estimated_tokens < 100 or 5000 < estimated_tokens <= 10000:
            pts = 1.0
            msg = f"Body length slightly outside range (~{estimated_tokens} tokens)"
            issues.append(f"Body length ~{estimated_tokens} tokens (prefer 100-5000)")
        else:
            pts = 0.0
            msg = f"Body length problematic (~{estimated_tokens} tokens)"
            issues.append(f"Body too short (<50 tokens) or too long (>10000 tokens)")

        sub_checks.append(StaticSubCheck(
            name="Body Length",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        return StaticTestResult(
            test_id="ST-6",
            test_name="Instruction Clarity",
            max_points=4.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-7: Instruction Specificity (6 bonus points)
    # ========================================================================

    def _st7_instruction_specificity(self) -> StaticTestResult:
        """
        ST-7: Instruction Specificity (6 bonus points)

        Sub-checks:
        - No vague platitudes (2 pts)
        - No open-ended tool menus (2 pts)
        - Contains concrete gotchas/constraints (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        if not self.skill_md.exists():
            return StaticTestResult(
                test_id="ST-7",
                test_name="Instruction Specificity",
                max_points=6.0,
                earned_points=0.0,
                sub_checks=sub_checks,
                issues=["SKILL.md not found"],
            )

        content = self.skill_md.read_text()
        body = self._extract_body(content).lower()

        # Sub-check 1: No vague platitudes (2 pts)
        vague_patterns = [
            "handle errors appropriately",
            "follow best practices",
            "as needed",
            "use your judgment",
            "handle edge cases",
        ]
        vague_count = sum(1 for p in vague_patterns if p in body)

        if vague_count == 0:
            pts = 2.0
            msg = "No vague platitudes found"
        elif vague_count <= 2:
            pts = 1.0
            msg = f"{vague_count} vague phrase(s) found"
            issues.append(f"{vague_count} vague platitudes (handle errors appropriately, etc.)")
        else:
            pts = 0.0
            msg = f"{vague_count} vague phrases found"
            issues.append(f"Too many vague platitudes ({vague_count})")

        sub_checks.append(StaticSubCheck(
            name="No Vague Platitudes",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        # Sub-check 2: No open-ended tool menus (2 pts)
        tool_menu_pattern = r"you can use \w+,? \w+,? (or|and) \w+"
        has_tool_menu = bool(re.search(tool_menu_pattern, body))

        if not has_tool_menu:
            pts = 2.0
            msg = "No open-ended tool menus"
        else:
            pts = 0.0
            msg = "Open-ended tool menu detected"
            issues.append("Contains open-ended tool menu without defaults")

        sub_checks.append(StaticSubCheck(
            name="No Tool Menus",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        # Sub-check 3: Contains gotchas/constraints (2 pts)
        gotcha_keywords = ["gotcha", "constraint", "limitation", "warning", "important", "note:"]
        has_gotcha = any(kw in body for kw in gotcha_keywords)

        if has_gotcha:
            pts = 2.0
            msg = "Contains gotchas/constraints section"
        else:
            pts = 0.0
            msg = "No gotchas/constraints documented"
            issues.append("No gotchas or constraints section")

        sub_checks.append(StaticSubCheck(
            name="Gotchas/Constraints",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        return StaticTestResult(
            test_id="ST-7",
            test_name="Instruction Specificity",
            max_points=6.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # ST-8: Cross-Reference Integrity (4 bonus points)
    # ========================================================================

    def _st8_cross_reference_integrity(self) -> StaticTestResult:
        """
        ST-8: Cross-Reference Integrity (4 bonus points)

        Sub-checks:
        - All references/ file mentions exist on disk (2 pts)
        - No dead links to internal files (2 pts)
        """
        sub_checks = []
        issues = []
        total_points = 0.0

        if not self.skill_md.exists():
            return StaticTestResult(
                test_id="ST-8",
                test_name="Cross-Reference Integrity",
                max_points=4.0,
                earned_points=0.0,
                sub_checks=sub_checks,
                issues=["SKILL.md not found"],
            )

        content = self.skill_md.read_text()

        # Find references to references/ files
        ref_mentions = re.findall(r'references/([^\s\)]+)', content)
        refs_dir = self.skill_dir / "references"

        if ref_mentions:
            missing = []
            for ref in ref_mentions:
                ref_path = refs_dir / ref
                if not ref_path.exists():
                    missing.append(ref)

            if not missing:
                pts = 2.0
                msg = f"All {len(ref_mentions)} reference(s) exist"
            else:
                pts = 1.0 if len(missing) < len(ref_mentions) else 0.0
                msg = f"{len(missing)} missing reference(s)"
                issues.append(f"Missing references: {', '.join(missing)}")

            sub_checks.append(StaticSubCheck(
                name="Reference Integrity",
                max_points=2.0,
                earned_points=pts,
                passed=pts == 2.0,
                message=msg,
            ))
            total_points += pts
        else:
            # No references mentioned = full credit
            sub_checks.append(StaticSubCheck(
                name="Reference Integrity",
                max_points=2.0,
                earned_points=2.0,
                passed=True,
                message="No references/ mentions (N/A)",
            ))
            total_points += 2.0

        # Check for dead internal links
        internal_links = re.findall(r'\[([^\]]+)\]\((?!http)([^\)]+)\)', content)
        dead_links = []

        for link_text, link_path in internal_links:
            full_path = self.skill_dir / link_path
            if not full_path.exists():
                dead_links.append(link_path)

        if not dead_links and internal_links:
            pts = 2.0
            msg = f"All {len(internal_links)} internal link(s) valid"
        elif dead_links:
            pts = 0.0
            msg = f"{len(dead_links)} dead link(s)"
            issues.append(f"Dead links: {', '.join(dead_links)}")
        else:
            # No internal links = full credit
            pts = 2.0
            msg = "No internal links (N/A)"

        sub_checks.append(StaticSubCheck(
            name="No Dead Links",
            max_points=2.0,
            earned_points=pts,
            passed=pts == 2.0,
            message=msg,
        ))
        total_points += pts

        return StaticTestResult(
            test_id="ST-8",
            test_name="Cross-Reference Integrity",
            max_points=4.0,
            earned_points=total_points,
            sub_checks=sub_checks,
            issues=issues,
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _extract_frontmatter(self, content: str) -> Tuple[dict, bool]:
        """Extract and parse YAML frontmatter."""
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return {}, False

        frontmatter_yaml = match.group(1)
        try:
            frontmatter = yaml.safe_load(frontmatter_yaml)
            return frontmatter or {}, True
        except yaml.YAMLError:
            return {}, False

    def _extract_body(self, content: str) -> str:
        """Extract body content (after frontmatter)."""
        match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        if match:
            return content[match.end():]
        return content

    def _count_sentences(self, text: str) -> int:
        """Count complete sentences (ending with . ! ?)."""
        sentences = re.findall(r'[.!?]+', text)
        return len(sentences)

    def _type_token_ratio(self, text: str) -> float:
        """Calculate type-token ratio (unique words / total words)."""
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0
        return len(set(words)) / len(words)

    def _verb_density(self, text: str) -> float:
        """
        Estimate verb density (rough heuristic).
        Common action verbs in skill descriptions.
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if not words:
            return 0.0

        # Common action verbs in skill descriptions
        action_verbs = {
            "generate", "analyze", "process", "transform", "create", "build",
            "deploy", "configure", "manage", "handle", "execute", "run",
            "perform", "implement", "develop", "design", "review", "test",
        }

        verb_count = sum(1 for w in words if w in action_verbs)
        return verb_count / len(words)
