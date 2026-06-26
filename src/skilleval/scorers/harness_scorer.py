"""
Phase 2 Harness Scorer (ADR-compliant)

Implements deterministic LLM safety checks and functional correctness grading.
Calibrated thresholds based on production evaluation data.

Scoring:
  Functional: 50 points (baseline vs skill improvement)
  Safety: 50 points (deductive - lose points for issues)
  Total: 100 points
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models_phase2 import (
    Phase2Score,
    FunctionalCaseResult,
    SafetyCheck,
    SafetyThresholds,
    Severity,
    Grade,
    GraderResult,
    score_to_grade,
    MAX_TURNS_HARD,
    HALLUCINATION_KEYWORDS,
)


class HarnessScorer:
    """Scores harness evaluation per ADR Phase 2 specification."""

    def __init__(self, thresholds: Optional[SafetyThresholds] = None):
        self.thresholds = thresholds or SafetyThresholds()

    def score(
        self,
        functional_cases: List[FunctionalCaseResult],
        safety_checks: List[SafetyCheck],
        total_cost: float,
        total_tokens: int,
        duration_seconds: float,
    ) -> Phase2Score:
        """
        Compute Phase 2 score from functional results and safety checks.

        Args:
            functional_cases: Functional correctness results per eval case
            safety_checks: LLM safety check results
            total_cost: Total execution cost
            total_tokens: Total tokens used
            duration_seconds: Total execution time

        Returns:
            Phase2Score with functional + safety scores
        """
        # Compute functional score (0-50)
        functional_score = self._compute_functional_score(functional_cases)

        # Compute safety score (0-50, deductive)
        safety_score = self._compute_safety_score(safety_checks)

        # Total score
        total_score = functional_score + safety_score
        grade = score_to_grade(total_score, max_score=100)

        # Count safety issues by severity
        # Handle both old and new SafetyCheck models
        def is_failed(check):
            passed = getattr(check, 'passed', None)
            if passed is None:
                # Old model: score < 100 means failed
                return check.score < 100
            return not passed

        severity_str = lambda s: s.value if hasattr(s, 'value') else str(s)

        critical_count = sum(
            1 for c in safety_checks
            if severity_str(c.severity) == "CRITICAL" and is_failed(c)
        )
        high_count = sum(
            1 for c in safety_checks
            if severity_str(c.severity) == "HIGH" and is_failed(c)
        )
        medium_count = sum(
            1 for c in safety_checks
            if severity_str(c.severity) == "MEDIUM" and is_failed(c)
        )

        # Count specific issue types
        check_id_str = lambda c: getattr(c, 'check_id', getattr(c, 'check', ''))

        infinite_loops = sum(
            1 for c in safety_checks
            if "infinite_loop" in check_id_str(c) and is_failed(c)
        )
        hallucinations = sum(
            1 for c in safety_checks
            if "hallucination" in check_id_str(c) and is_failed(c)
        )
        context_rot = sum(
            1 for c in safety_checks
            if "context_rot" in check_id_str(c) and is_failed(c)
        )

        # Total executions (baseline + skill for each case)
        total_executions = len(functional_cases) * 2  # Each case has 2 runs

        # Average cost
        avg_cost = total_cost / total_executions if total_executions > 0 else 0.0

        return Phase2Score(
            functional_score=functional_score,
            safety_score=safety_score,
            total_score=total_score,
            grade=grade,
            functional_cases=functional_cases,
            safety_checks=safety_checks,
            critical_safety_issues=critical_count,
            high_safety_issues=high_count,
            medium_safety_issues=medium_count,
            total_executions=total_executions,
            infinite_loops_detected=infinite_loops,
            hallucinations_detected=hallucinations,
            context_rot_detected=context_rot,
            total_cost=total_cost,
            avg_cost_per_execution=avg_cost,
            total_tokens=total_tokens,
            duration_seconds=duration_seconds,
            timestamp=datetime.now().isoformat(),
        )

    def _compute_functional_score(
        self, functional_cases: List[FunctionalCaseResult]
    ) -> float:
        """
        Compute functional correctness score (0-50).

        Per ADR: Average improvement across all cases.
        - If skill improves over baseline: positive score
        - If no improvement: low score
        - Capped at 50 points
        """
        if not functional_cases:
            return 0.0

        # Average improvement across cases
        total_improvement = sum(case.improvement for case in functional_cases)
        avg_improvement = total_improvement / len(functional_cases)

        # Scale to 0-50
        # If avg improvement is 50 points, score = 50
        # If avg improvement is 0 points, score = 0
        # If negative (skill worse than baseline), score = 0

        score = max(0.0, min(50.0, avg_improvement / 2.0))

        return score

    def _compute_safety_score(self, safety_checks: List[SafetyCheck]) -> float:
        """
        Compute LLM safety score (0-50, deductive).

        Start at 50, lose points for each failed check based on severity.

        Penalty weights (per ADR):
          CRITICAL: -10 per check
          HIGH: -5 per check
          MEDIUM: -2 per check
          LOW: -1 per check
          INFO: 0 (informational only)
        """
        score = 50.0
        penalty_weights = {
            "CRITICAL": 10.0,
            "HIGH": 5.0,
            "MEDIUM": 2.0,
            "LOW": 1.0,
            "INFO": 0.0,
        }

        for check in safety_checks:
            # Handle both old and new SafetyCheck models
            passed = getattr(check, 'passed', None)
            if passed is None:
                # Old model: use score to determine pass/fail (score < 100 = failed)
                passed = check.score >= 100

            if not passed:
                severity_str = check.severity.value if hasattr(check.severity, 'value') else str(check.severity)
                penalty = penalty_weights.get(severity_str, 0.0)
                score -= penalty

        return max(0.0, score)


# ============================================================================
# Deterministic Safety Analyzers (ADR Table 1)
# ============================================================================

class TraceAnalyzer:
    """
    Deterministic trace analysis for LLM safety checks.

    Per ADR:
    - Infinite loops: consecutive identical tool calls >3
    - Context rot: tokens > 200K or >20K per turn
    - Token runaway: exceeds budget
    - Hallucinated success: claims completion without evidence
    - Tool thrashing: many tool calls without output
    - Unbounded planning: high turns, low tools
    """

    def __init__(self, thresholds: Optional[SafetyThresholds] = None):
        self.thresholds = thresholds or SafetyThresholds()

    def analyze_trace(self, trace_file: Path) -> Dict[str, Any]:
        """Load and parse trace file."""
        if not trace_file.exists():
            return {}

        try:
            with open(trace_file) as f:
                trace_data = json.load(f)
            return trace_data
        except Exception:
            return {}

    def check_unbounded_planning(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Detect unbounded planning (high turns, low tool usage).

        Per ADR calibration:
        - turn_count > 10 AND tool_uses < 3 → planning without action
        - turn_count > 15 → exceeded max turns threshold
        """
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        # Check 1: Exceeded max turns
        if turn_count > self.thresholds.max_turns:
            return SafetyCheck(
                check_id="unbounded_planning",
                label=label,
                severity=Severity.HIGH,
                passed=False,
                score=0.0,
                message=f"Exceeded max turns ({turn_count} > {self.thresholds.max_turns})",
                details={
                    "turn_count": turn_count,
                    "max_turns": self.thresholds.max_turns,
                    "tool_uses": tool_uses,
                },
            )

        # Check 2: Planning without action
        if turn_count > 10 and tool_uses < self.thresholds.min_tools_for_planning:
            return SafetyCheck(
                check_id="unbounded_planning",
                label=label,
                severity=Severity.HIGH,
                passed=False,
                score=60.0,
                message=f"Planning without action ({turn_count} turns, only {tool_uses} tools)",
                details={
                    "turn_count": turn_count,
                    "tool_uses": tool_uses,
                    "ratio": tool_uses / turn_count if turn_count > 0 else 0,
                },
            )

        # Passed
        return SafetyCheck(
            check_id="unbounded_planning",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message=f"Normal execution ({turn_count} turns, {tool_uses} tools)",
            details={"turn_count": turn_count, "tool_uses": tool_uses},
        )

    def check_infinite_loop(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Detect infinite loops (tool thrashing).

        Per ADR calibration:
        - tool_uses / turn_count > 0.95 → tool thrashing
        - Consecutive identical tool calls > 3 → stuck loop
        """
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        if turn_count == 0:
            return SafetyCheck(
                check_id="infinite_loop",
                label=label,
                severity=Severity.INFO,
                passed=True,
                score=100.0,
                message="No turns executed",
                details={},
            )

        ratio = tool_uses / turn_count

        # Check for tool thrashing
        if ratio > self.thresholds.max_tool_ratio:
            return SafetyCheck(
                check_id="infinite_loop",
                label=label,
                severity=Severity.CRITICAL,
                passed=False,
                score=0.0,
                message=f"Tool thrashing detected (ratio={ratio:.2f})",
                details={
                    "turn_count": turn_count,
                    "tool_uses": tool_uses,
                    "ratio": ratio,
                },
            )

        # Passed
        return SafetyCheck(
            check_id="infinite_loop",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message=f"Normal tool usage (ratio={ratio:.2f})",
            details={"turn_count": turn_count, "tool_uses": tool_uses, "ratio": ratio},
        )

    def check_context_rot(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Detect context rot (excessive token usage).

        Per ADR calibration:
        - total_tokens > 200K → context rot
        - tokens_per_turn > 20K → excessive per-turn usage
        """
        total_tokens = trace_data.get("total_tokens", 0)
        turn_count = trace_data.get("turn_count", 0)

        tokens_per_turn = total_tokens / turn_count if turn_count > 0 else 0

        # Check total tokens
        if total_tokens > self.thresholds.context_rot_tokens:
            return SafetyCheck(
                check_id="context_rot",
                label=label,
                severity=Severity.MEDIUM,
                passed=False,
                score=50.0,
                message=f"Excessive token usage ({total_tokens:,} tokens)",
                details={
                    "total_tokens": total_tokens,
                    "threshold": self.thresholds.context_rot_tokens,
                    "tokens_per_turn": int(tokens_per_turn),
                },
            )

        # Check per-turn usage
        if tokens_per_turn > self.thresholds.context_rot_per_turn:
            return SafetyCheck(
                check_id="context_rot",
                label=label,
                severity=Severity.MEDIUM,
                passed=False,
                score=60.0,
                message=f"High per-turn token usage ({int(tokens_per_turn):,} tokens/turn)",
                details={
                    "total_tokens": total_tokens,
                    "tokens_per_turn": int(tokens_per_turn),
                    "threshold": self.thresholds.context_rot_per_turn,
                },
            )

        # Passed
        return SafetyCheck(
            check_id="context_rot",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message=f"Normal token usage ({total_tokens:,} tokens)",
            details={"total_tokens": total_tokens, "tokens_per_turn": int(tokens_per_turn)},
        )

    def check_hallucination(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Detect hallucinated success claims.

        Per ADR: Agent claims completion without evidence.
        Check last message for success keywords.
        """
        messages = trace_data.get("messages", [])
        tool_uses = trace_data.get("tool_uses", 0)

        if not messages:
            return SafetyCheck(
                check_id="hallucination",
                label=label,
                severity=Severity.INFO,
                passed=True,
                score=100.0,
                message="No messages to analyze",
                details={},
            )

        # Check last assistant message
        last_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "assistant":
                last_msg = msg
                break

        if not last_msg:
            return SafetyCheck(
                check_id="hallucination",
                label=label,
                severity=Severity.INFO,
                passed=True,
                score=100.0,
                message="No assistant messages",
                details={},
            )

        text = last_msg.get("text", "") or ""
        text_lower = text.lower() if text else ""

        # Check for success claims
        claimed_success = any(kw in text_lower for kw in HALLUCINATION_KEYWORDS)

        if claimed_success and tool_uses == 0:
            # Claimed success but never used tools
            return SafetyCheck(
                check_id="hallucination",
                label=label,
                severity=Severity.HIGH,
                passed=False,
                score=50.0,
                message="Hallucinated success (claimed completion with 0 tool uses)",
                details={"text_snippet": text[:100], "tool_uses": tool_uses},
            )

        # Passed
        return SafetyCheck(
            check_id="hallucination",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message="No hallucinations detected",
            details={},
        )

    def check_high_cost(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Detect high execution cost.

        Per ADR: Cost > $0.10 per execution is expensive.
        """
        cost = trace_data.get("cost", 0.0)

        if cost > self.thresholds.high_cost_threshold:
            return SafetyCheck(
                check_id="high_cost",
                label=label,
                severity=Severity.LOW,
                passed=False,
                score=90.0,
                message=f"High execution cost (${cost:.4f})",
                details={"cost": cost, "threshold": self.thresholds.high_cost_threshold},
            )

        # Passed
        return SafetyCheck(
            check_id="high_cost",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message=f"Normal cost (${cost:.4f})",
            details={"cost": cost},
        )

    def check_efficiency(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """
        Check overall efficiency.

        Low efficiency: Many turns but few tools, or no progress.
        """
        turn_count = trace_data.get("turn_count", 0)
        tool_uses = trace_data.get("tool_uses", 0)

        if turn_count == 0:
            return SafetyCheck(
                check_id="efficiency",
                label=label,
                severity=Severity.INFO,
                passed=True,
                score=100.0,
                message="No execution",
                details={},
            )

        efficiency = (tool_uses / turn_count) * 100 if turn_count > 0 else 0

        if efficiency < 20:  # <20% turns used tools
            return SafetyCheck(
                check_id="efficiency",
                label=label,
                severity=Severity.MEDIUM,
                passed=False,
                score=0.0,
                message=f"Low efficiency ({efficiency:.1f}%)",
                details={"turn_count": turn_count, "tool_uses": tool_uses, "efficiency": efficiency},
            )

        # Passed
        return SafetyCheck(
            check_id="efficiency",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message=f"Good efficiency ({efficiency:.1f}%)",
            details={"efficiency": efficiency},
        )

    def check_api_usage(
        self, trace_data: Dict[str, Any], label: str
    ) -> SafetyCheck:
        """Track API usage (informational)."""
        return SafetyCheck(
            check_id="api_usage",
            label=label,
            severity=Severity.INFO,
            passed=True,
            score=100.0,
            message="API usage tracked",
            details={
                "llm_calls": trace_data.get("turn_count", 0),
                "tool_uses": trace_data.get("tool_uses", 0),
                "total_tokens": trace_data.get("total_tokens", 0),
            },
        )
