"""
Phase 2 Models: Harness Evaluation (ADR-compliant)

This module defines the data structures for Phase 2 evaluation:
- Functional correctness: Deterministic grading (file_exists, content_match, json_schema)
- LLM Safety: Deterministic trace analysis (no LLM-as-judge)
- Skill Lift: Baseline vs skill comparison

Per ADR:
- When integrated with Phase 1, weights are 30/30/40 (Static/Security/Harness)
- Phase 2 standalone: 100 points (Functional 50 + Safety 50)
- Dual-score reporting: Phase 1 (packaging) + Phase 2 (runtime) shown separately
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class Severity(str, Enum):
    """Safety check severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Grade(str, Enum):
    """Grade levels."""
    A = "A"  # 90-100
    B = "B"  # 80-89
    C = "C"  # 70-79
    D = "D"  # 60-69
    F = "F"  # 0-59


# ============================================================================
# Functional Correctness (Deterministic Grading)
# ============================================================================

class GraderResult(BaseModel):
    """Result from a single deterministic grader."""
    type: str  # file_exists, content_match, json_schema, etc.
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class FunctionalCaseResult(BaseModel):
    """Functional correctness result for one eval case."""
    case_id: str
    baseline_score: float = Field(ge=0, le=100)
    skill_score: float = Field(ge=0, le=100)
    improvement: float  # skill_score - baseline_score
    improvement_pct: float  # (improvement / 100) * 100
    baseline_checks: List[GraderResult] = Field(default_factory=list)
    skill_checks: List[GraderResult] = Field(default_factory=list)


# ============================================================================
# LLM Safety (Deterministic Trace Analysis)
# ============================================================================

class SafetyCheck(BaseModel):
    """LLM safety check result (deterministic, no LLM-as-judge)."""
    check_id: str  # e.g., "unbounded_planning", "infinite_loop"
    label: str  # e.g., "case1_baseline", "case1_skill"
    severity: Severity
    passed: bool  # True if no issue, False if issue detected
    score: float = Field(ge=0, le=100, description="100 if passed, penalty if failed")
    details: Dict[str, Any] = Field(default_factory=dict)
    message: str


# Calibrated thresholds per ADR review
# These are based on production data from jira-comment-poster evaluation

# Infinite loop detection
MAX_TURNS_HARD = 15  # ADR: Lower from 25 to 15 (more aggressive)
MAX_TURN_TOOL_RATIO = 0.95  # Tool thrashing: >95% turns using tools
MIN_TOOLS_FOR_PLANNING = 3  # Unbounded planning if >10 turns, <3 tools

# Context rot detection
CONTEXT_ROT_TOKEN_THRESHOLD = 200_000  # Tokens > 200K flagged as rot
CONTEXT_ROT_PER_TURN_THRESHOLD = 20_000  # >20K tokens/turn is excessive

# Hallucination detection
HALLUCINATION_KEYWORDS = [
    "completed successfully",
    "task is done",
    "finished",
    "all set",
    "success",
]

# Cost thresholds
HIGH_COST_THRESHOLD = 0.10  # >$0.10 per execution is expensive

# Repetition detection
REPETITION_WINDOW = 3  # Check last N tool calls for identical patterns


class SafetyThresholds(BaseModel):
    """Configurable safety thresholds."""
    max_turns: int = MAX_TURNS_HARD
    max_tool_ratio: float = MAX_TURN_TOOL_RATIO
    min_tools_for_planning: int = MIN_TOOLS_FOR_PLANNING
    context_rot_tokens: int = CONTEXT_ROT_TOKEN_THRESHOLD
    context_rot_per_turn: int = CONTEXT_ROT_PER_TURN_THRESHOLD
    high_cost_threshold: float = HIGH_COST_THRESHOLD
    repetition_window: int = REPETITION_WINDOW


# ============================================================================
# Phase 2 Combined Score
# ============================================================================

class Phase2Score(BaseModel):
    """Phase 2 harness evaluation score."""
    functional_score: float = Field(ge=0, le=50, description="Functional correctness out of 50")
    safety_score: float = Field(ge=0, le=50, description="LLM safety out of 50")
    total_score: float = Field(ge=0, le=100, description="Functional + Safety")
    grade: Grade

    # Functional results per case
    functional_cases: List[FunctionalCaseResult] = Field(default_factory=list)

    # Safety checks
    safety_checks: List[SafetyCheck] = Field(default_factory=list)
    critical_safety_issues: int = 0
    high_safety_issues: int = 0
    medium_safety_issues: int = 0

    # Metrics
    total_executions: int  # baseline + skill runs
    infinite_loops_detected: int
    hallucinations_detected: int
    context_rot_detected: int

    # Performance
    total_cost: float
    avg_cost_per_execution: float
    total_tokens: int
    duration_seconds: float
    timestamp: str


# ============================================================================
# Dual-Score Report (Phase 1 + Phase 2)
# ============================================================================

class DualScoreReport(BaseModel):
    """
    Dual-score evaluation report: Phase 1 (packaging) + Phase 2 (runtime).

    Per ADR recommendation: show both phases separately, don't renormalize.
    Overall grade is average of Phase 1 and Phase 2 grades.
    """
    skill_name: str
    skill_version: Optional[str] = None

    # Phase 1: Static + Security (packaging quality)
    phase1_score: float = Field(ge=0, le=100)
    phase1_grade: Grade
    phase1_static: float = Field(ge=0, le=50)
    phase1_security: float = Field(ge=0, le=50)
    phase1_publish_decision: str
    phase1_auto_reject: bool

    # Phase 2: Harness (runtime effectiveness)
    phase2_score: float = Field(ge=0, le=100)
    phase2_grade: Grade
    phase2_functional: float = Field(ge=0, le=50)
    phase2_safety: float = Field(ge=0, le=50)

    # Overall
    overall_grade: Grade
    overall_recommendation: str

    duration_seconds: float
    timestamp: str


def score_to_grade(score: float, max_score: float = 100) -> Grade:
    """Convert numeric score to letter grade."""
    percentage = (score / max_score) * 100

    if percentage >= 90:
        return Grade.A
    elif percentage >= 80:
        return Grade.B
    elif percentage >= 70:
        return Grade.C
    elif percentage >= 60:
        return Grade.D
    else:
        return Grade.F


def average_grades(grade1: Grade, grade2: Grade) -> Grade:
    """Average two letter grades."""
    grade_values = {
        Grade.A: 95,
        Grade.B: 85,
        Grade.C: 75,
        Grade.D: 65,
        Grade.F: 50,
    }

    avg = (grade_values[grade1] + grade_values[grade2]) / 2
    return score_to_grade(avg, max_score=100)
