"""
Pillar 3: Harness

Functional correctness testing with baseline comparison.
"""

import time
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from skilleval.models import (
    HarnessConfig,
    HarnessResult,
    FunctionalResult,
    SafetyCheck,
    GraderResult,
    Grader,
    EvalCase,
    Severity,
    Grade,
)
from skilleval.utils.logger import logger
from skilleval.utils.multi_provider_agent import MultiProviderExecutorSync, TraceAnalyzer


class HarnessPillar:
    """Harness evaluation pillar - functional correctness."""

    def __init__(self, config: HarnessConfig):
        self.config = config
        self.executor = MultiProviderExecutorSync(config)
        self.trace_analyzer = TraceAnalyzer()

    def run(self, skill_path: Path, eval_cases: List[EvalCase]) -> HarnessResult:
        """
        Run harness evaluation.

        Args:
            skill_path: Path to skill directory
            eval_cases: List of evaluation cases

        Returns:
            HarnessResult
        """
        start_time = time.time()

        if not eval_cases:
            logger.warning("No eval cases found - skipping harness")
            return self._placeholder_result(time.time() - start_time)

        functional_results = []
        safety_checks = []

        # Run functional tests for each eval case
        for eval_case in eval_cases:
            logger.info(f"Running eval case: {eval_case.id}")

            # Run baseline (without skill)
            baseline_result = self._run_baseline(skill_path, eval_case)

            # Run with skill
            skill_result = self._run_with_skill(skill_path, eval_case)

            # Compare results
            functional_result = self._compare_results(
                eval_case, baseline_result, skill_result
            )
            functional_results.append(functional_result)

            # Analyze traces for safety issues
            baseline_trace = baseline_result.get("trace_file")
            skill_trace = skill_result.get("trace_file")

            if baseline_trace:
                baseline_safety = self._analyze_trace_safety(baseline_trace, f"{eval_case.id}_baseline")
                safety_checks.extend(baseline_safety)

            if skill_trace:
                skill_safety = self._analyze_trace_safety(skill_trace, f"{eval_case.id}_skill")
                safety_checks.extend(skill_safety)

        # Calculate scores
        duration = time.time() - start_time
        return self._calculate_scores(functional_results, safety_checks, duration)

    def _placeholder_result(self, duration: float) -> HarnessResult:
        """Return placeholder result when harness can't run."""
        return HarnessResult(
            score=70.0,
            grade=Grade.C,
            functional_score=70.0,
            safety_score=70.0,
            owasp_llm_score=70.0,
            functional_results=[],
            safety_checks=[],
            owasp_llm=None,
            duration_seconds=duration,
        )

    def _run_baseline(
        self, skill_path: Path, eval_case: EvalCase
    ) -> Dict[str, Any]:
        """
        Run eval case WITHOUT the skill (baseline).

        This simulates the LLM attempting the task without skill guidance.
        """
        # Create temporary workspace
        import tempfile
        workspace = Path(tempfile.mkdtemp(prefix="skilleval_baseline_"))

        try:
            result = self.executor.execute_baseline(
                skill_path=skill_path,
                eval_case=eval_case.model_dump(),
                workspace=workspace,
            )
            return result
        except Exception as e:
            logger.warning(f"Baseline execution failed: {e}")
            return {
                "workspace": workspace,
                "trace_file": None,
                "error": str(e),
            }

    def _run_with_skill(
        self, skill_path: Path, eval_case: EvalCase
    ) -> Dict[str, Any]:
        """
        Run eval case WITH the skill activated.

        This tests if the skill improves the LLM's performance.
        """
        # Create temporary workspace
        import tempfile
        workspace = Path(tempfile.mkdtemp(prefix="skilleval_skill_"))

        try:
            result = self.executor.execute_with_skill(
                skill_path=skill_path,
                eval_case=eval_case.model_dump(),
                workspace=workspace,
            )
            return result
        except Exception as e:
            logger.warning(f"Skill execution failed: {e}")
            return {
                "workspace": workspace,
                "trace_file": None,
                "error": str(e),
            }

    def _compare_results(
        self,
        eval_case: EvalCase,
        baseline: Dict[str, Any],
        skill: Dict[str, Any],
    ) -> FunctionalResult:
        """
        Compare baseline vs skill results using deterministic graders.

        Args:
            eval_case: The evaluation case
            baseline: Baseline run results
            skill: With-skill run results

        Returns:
            FunctionalResult with scores and improvement metrics
        """
        # Run graders on baseline
        baseline_checks = self._run_graders(
            eval_case.graders, baseline.get("workspace")
        )

        # Run graders on skill
        skill_checks = self._run_graders(
            eval_case.graders, skill.get("workspace")
        )

        # Calculate scores
        baseline_score = self._calculate_grader_score(baseline_checks)
        skill_score = self._calculate_grader_score(skill_checks)

        improvement = skill_score - baseline_score
        improvement_pct = (improvement / 100) * 100 if baseline_score > 0 else 0

        return FunctionalResult(
            case_id=eval_case.id,
            baseline_score=baseline_score,
            skill_score=skill_score,
            improvement=improvement,
            improvement_pct=improvement_pct,
            baseline_checks=baseline_checks,
            skill_checks=skill_checks,
        )

    def _run_graders(
        self, graders: List[Grader], workspace: Optional[Path]
    ) -> List[GraderResult]:
        """
        Run deterministic graders on workspace.

        Args:
            graders: List of grader definitions
            workspace: Path to workspace directory

        Returns:
            List of GraderResult
        """
        if not graders or not workspace:
            return []

        results = []
        for grader in graders:
            result = self._run_single_grader(grader, workspace)
            results.append(result)

        return results

    def _run_single_grader(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """
        Run a single deterministic grader.

        Supported grader types:
        - file_exists: Check if file exists
        - json_schema: Validate JSON against schema
        - content_match: Check file content matches pattern
        - command_output: Run command and check output
        - exit_code: Check command exit code
        """
        grader_type = grader.type

        if grader_type == "file_exists":
            return self._grade_file_exists(grader, workspace)
        elif grader_type == "json_schema":
            return self._grade_json_schema(grader, workspace)
        elif grader_type == "content_match":
            return self._grade_content_match(grader, workspace)
        elif grader_type == "command_output":
            return self._grade_command_output(grader, workspace)
        elif grader_type == "exit_code":
            return self._grade_exit_code(grader, workspace)
        else:
            return GraderResult(
                type=grader_type,
                passed=False,
                message=f"Unknown grader type: {grader_type}",
            )

    def _grade_file_exists(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """Check if file exists."""
        file_path = workspace / grader.path
        exists = file_path.exists()

        return GraderResult(
            type="file_exists",
            passed=exists,
            message=f"File {'exists' if exists else 'does not exist'}: {grader.path}",
        )

    def _grade_json_schema(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """Validate JSON file against schema."""
        file_path = workspace / grader.path

        if not file_path.exists():
            return GraderResult(
                type="json_schema",
                passed=False,
                message=f"File not found: {grader.path}",
            )

        try:
            with open(file_path) as f:
                data = json.load(f)

            # TODO: Use jsonschema library for validation
            # For now, just check if it's valid JSON
            return GraderResult(
                type="json_schema",
                passed=True,
                message=f"Valid JSON: {grader.path}",
            )
        except Exception as e:
            return GraderResult(
                type="json_schema",
                passed=False,
                message=f"Invalid JSON: {e}",
            )

    def _grade_content_match(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """Check if file content matches pattern."""
        import re

        file_path = workspace / grader.path

        if not file_path.exists():
            return GraderResult(
                type="content_match",
                passed=False,
                message=f"File not found: {grader.path}",
            )

        try:
            content = file_path.read_text()
            matches = re.search(grader.pattern, content) is not None

            return GraderResult(
                type="content_match",
                passed=matches,
                message=f"Pattern {'matches' if matches else 'does not match'}",
            )
        except Exception as e:
            return GraderResult(
                type="content_match",
                passed=False,
                message=f"Error reading file: {e}",
            )

    def _grade_command_output(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """Run command and check output."""
        import re

        try:
            result = subprocess.run(
                grader.command,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=30,
            )

            output = result.stdout + result.stderr
            matches = re.search(grader.expected_pattern, output) is not None

            return GraderResult(
                type="command_output",
                passed=matches,
                message=f"Command output {'matches' if matches else 'does not match'} pattern",
                details={"output": output[:200]},
            )
        except Exception as e:
            return GraderResult(
                type="command_output",
                passed=False,
                message=f"Command failed: {e}",
            )

    def _grade_exit_code(
        self, grader: Grader, workspace: Path
    ) -> GraderResult:
        """Check command exit code."""
        try:
            result = subprocess.run(
                grader.command,
                cwd=workspace,
                capture_output=True,
                timeout=30,
            )

            passed = result.returncode == grader.expected_code

            return GraderResult(
                type="exit_code",
                passed=passed,
                message=f"Exit code: {result.returncode} (expected {grader.expected_code})",
            )
        except Exception as e:
            return GraderResult(
                type="exit_code",
                passed=False,
                message=f"Command failed: {e}",
            )

    def _calculate_grader_score(self, grader_results: List[GraderResult]) -> float:
        """Calculate score from grader results (0-100)."""
        if not grader_results:
            return 0.0

        passed = sum(1 for r in grader_results if r.passed)
        total = len(grader_results)

        return (passed / total) * 100

    def _analyze_trace_safety(self, trace_file: Path, label: str) -> List[SafetyCheck]:
        """
        Analyze a single trace file for LLM behavior issues.

        Args:
            trace_file: Path to trace.json file
            label: Label for this execution (e.g., "case1_baseline")

        Returns:
            List of SafetyCheck objects
        """
        checks = []

        # Load and analyze trace
        trace_data = self.trace_analyzer.analyze_trace(trace_file)

        # 1. Unbounded Planning
        if self.trace_analyzer.detect_unbounded_planning(trace_data):
            checks.append(SafetyCheck(
                check=f"unbounded_planning_{label}",
                score=40.0,
                severity=Severity.HIGH,
                details={
                    "turns": trace_data["turn_count"],
                    "tool_uses": trace_data["tool_uses"],
                    "issue": "Agent took excessive turns without completing task"
                },
            ))

        # 2. Planning Without Action
        if self.trace_analyzer.detect_planning_without_action(trace_data):
            checks.append(SafetyCheck(
                check=f"planning_without_action_{label}",
                score=50.0,
                severity=Severity.MEDIUM,
                details={
                    "turns": trace_data["turn_count"],
                    "tool_uses": trace_data["tool_uses"],
                    "ratio": f"{trace_data['tool_uses']}/{trace_data['turn_count']}",
                    "issue": "Agent spent many turns thinking but not doing"
                },
            ))

        # 3. Context Rot
        if self.trace_analyzer.detect_context_rot(trace_data):
            checks.append(SafetyCheck(
                check=f"context_rot_{label}",
                score=60.0,
                severity=Severity.MEDIUM,
                details={
                    "total_tokens": trace_data["total_tokens"],
                    "turns": trace_data["turn_count"],
                    "tokens_per_turn": trace_data["total_tokens"] // max(1, trace_data["turn_count"]),
                    "issue": "Excessive token usage or approaching context limits"
                },
            ))

        # 4. Infinite Loops
        if self.trace_analyzer.detect_infinite_loops(trace_data):
            checks.append(SafetyCheck(
                check=f"infinite_loop_{label}",
                score=20.0,
                severity=Severity.CRITICAL,
                details={
                    "tool_uses": len(trace_data.get("tool_use_list", [])),
                    "turns": trace_data["turn_count"],
                    "issue": "Repetitive tool usage pattern detected"
                },
            ))

        # 5. Repetition
        if self.trace_analyzer.detect_repetition(trace_data):
            checks.append(SafetyCheck(
                check=f"repetition_{label}",
                score=70.0,
                severity=Severity.LOW,
                details={
                    "issue": "Agent is repeating similar responses"
                },
            ))

        # 6. Hallucinations
        hallucinations = self.trace_analyzer.detect_hallucinations(trace_data)
        if hallucinations:
            checks.append(SafetyCheck(
                check=f"hallucination_{label}",
                score=50.0,
                severity=Severity.HIGH,
                details={
                    "count": len(hallucinations),
                    "issues": hallucinations,
                },
            ))

        # 7. API Call Tracking
        api_counts = self.trace_analyzer.count_api_calls(trace_data)
        checks.append(SafetyCheck(
            check=f"api_usage_{label}",
            score=100.0,
            severity=Severity.INFO,
            details=api_counts,
        ))

        # 8. Efficiency Score
        efficiency = self.trace_analyzer.calculate_efficiency_score(trace_data)
        if efficiency < 60:
            checks.append(SafetyCheck(
                check=f"low_efficiency_{label}",
                score=efficiency,
                severity=Severity.MEDIUM,
                details={
                    "efficiency_score": efficiency,
                    "turns": trace_data["turn_count"],
                    "tool_uses": trace_data["tool_uses"],
                    "issue": "Agent operated inefficiently"
                },
            ))

        # 9. Cost Tracking
        cost = self.trace_analyzer.calculate_cost(trace_data)
        if cost > 0.10:  # More than 10 cents
            checks.append(SafetyCheck(
                check=f"high_cost_{label}",
                score=80.0,
                severity=Severity.LOW,
                details={
                    "cost_usd": cost,
                    "tokens": trace_data["total_tokens"],
                    "provider": trace_data.get("provider", "unknown"),
                },
            ))

        return checks

    def _run_safety_checks(
        self, skill_path: Path, functional_results: List[FunctionalResult]
    ) -> List[SafetyCheck]:
        """
        Legacy method - safety checks now run inline during evaluation.
        Kept for compatibility.
        """
        return []

    def _calculate_scores(
        self,
        functional_results: List[FunctionalResult],
        safety_checks: List[SafetyCheck],
        duration: float,
    ) -> HarnessResult:
        """Calculate final harness scores."""

        # Functional score: average improvement across eval cases
        if functional_results:
            functional_score = sum(r.skill_score for r in functional_results) / len(
                functional_results
            )
        else:
            functional_score = 0.0

        # Safety score: average across safety checks
        if safety_checks:
            safety_score = sum(c.score for c in safety_checks) / len(safety_checks)
        else:
            safety_score = 100.0  # No safety issues = perfect score

        # OWASP LLM score
        owasp_llm_score = 100.0  # Placeholder

        # Final harness score: weighted average
        # Functional: 60%, Safety: 30%, OWASP LLM: 10%
        final_score = (
            functional_score * 0.6 + safety_score * 0.3 + owasp_llm_score * 0.1
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

        return HarnessResult(
            score=final_score,
            grade=grade,
            functional_score=functional_score,
            safety_score=safety_score,
            owasp_llm_score=owasp_llm_score,
            functional_results=functional_results,
            safety_checks=safety_checks,
            owasp_llm=None,
            duration_seconds=duration,
        )
