"""
Phase 1 Models: Static Tests + Security (ADR-compliant)

This module defines the data structures for Phase 1 evaluation:
- Static Tests (ST-1 through ST-8): 50 points, additive
- Security (Layer 1 + Layer 2): 50 points, deductive with confidence weighting

Total: 0-100 points with A-F grading
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Finding severity levels with base penalties."""
    CRITICAL = "CRITICAL"  # Base penalty: 50 (instant zero at conf >= 0.7)
    HIGH = "HIGH"          # Base penalty: 12
    MEDIUM = "MEDIUM"      # Base penalty: 5
    LOW = "LOW"            # Base penalty: 2
    INFO = "INFO"          # Base penalty: 0 (informational only)


class Grade(str, Enum):
    """Grade levels per ADR."""
    A = "A"  # 90-100: Publish-ready, featured eligible
    B = "B"  # 80-89:  Publish-ready
    C = "C"  # 70-79:  Publish with advisory
    D = "D"  # 60-69:  Publish with acknowledgment
    F = "F"  # 0-59:   Blocked


class PublishDecision(str, Enum):
    """Publish decision based on score."""
    APPROVE = "APPROVE"                 # Grade A/B
    CONDITIONAL = "CONDITIONAL"         # Grade C
    REQUIRE_ACK = "REQUIRE_ACK"        # Grade D
    BLOCK = "BLOCK"                     # Grade F


# ============================================================================
# Static Tests (Pillar 1) - 50 points additive
# ============================================================================

@dataclass
class StaticSubCheck:
    """Individual sub-check within a static test."""
    name: str
    max_points: float
    earned_points: float
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class StaticTestResult(BaseModel):
    """Result from one static test (ST-1 through ST-8)."""
    test_id: str  # e.g., "ST-1", "ST-2"
    test_name: str  # e.g., "Frontmatter Validity"
    max_points: float
    earned_points: float
    sub_checks: List[StaticSubCheck] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)


class Phase1StaticScore(BaseModel):
    """Static tests pillar score (Phase 1, Pillar 1)."""
    score: float = Field(ge=0, le=50, description="Static tests score out of 50")
    grade: Grade
    tests: List[StaticTestResult] = Field(default_factory=list)

    # Breakdown by test
    st1_frontmatter: float = Field(ge=0, le=12)
    st2_description: float = Field(ge=0, le=10)
    st3_completeness: float = Field(ge=0, le=8)
    st4_script_quality: float = Field(ge=0, le=8)
    st5_eval_suite: float = Field(ge=0, le=8)
    st6_clarity: float = Field(ge=0, le=4)

    # Bonus (capped at 50 total)
    st7_specificity: float = Field(ge=0, le=6)
    st8_cross_reference: float = Field(ge=0, le=4)

    total_before_cap: float  # Score before 50-point cap
    issues: List[str] = Field(default_factory=list)


# ============================================================================
# Security (Pillar 2) - 50 points deductive with confidence weighting
# ============================================================================

class SecurityFinding(BaseModel):
    """Security finding from Layer 1 (built-in) or Layer 2 (SkillSpector)."""
    finding_id: str
    category: str  # e.g., "PI" (prompt injection), "DE" (data exfil), etc.
    severity: Severity
    confidence: float = Field(ge=0, le=1.0, description="Detection confidence")
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    pattern_matched: Optional[str] = None
    owasp_asi: Optional[str] = None  # e.g., "ASI01", "ASI02"
    layer: str = Field(description="Layer 1 (built-in) or Layer 2 (SkillSpector)")

    # Scoring
    base_penalty: float
    effective_penalty: float  # base_penalty × confidence
    is_scoreable: bool = Field(description="True if confidence >= 0.5")
    is_advisory: bool = Field(description="True if 0.3 <= confidence < 0.5")


class SecurityLayerResult(BaseModel):
    """Results from one security layer."""
    layer: str  # "Layer 1" or "Layer 2"
    scanner_name: str  # "built-in" or "SkillSpector"
    scanner_version: str
    findings: List[SecurityFinding] = Field(default_factory=list)
    duration_ms: float


class Phase1SecurityScore(BaseModel):
    """Security pillar score (Phase 1, Pillar 2)."""
    score: float = Field(ge=0, le=50, description="Security score out of 50")
    grade: Grade

    # Auto-reject flags
    has_critical_high_conf: bool = Field(
        description="CRITICAL finding with confidence >= 0.7 (instant F)"
    )
    below_security_floor: bool = Field(
        description="Score < 25/50 (50% floor, auto-reject)"
    )
    auto_reject: bool = Field(
        description="True if either reject condition met"
    )

    # Layer results
    layer1: SecurityLayerResult
    layer2: Optional[SecurityLayerResult] = None

    # Deduplicated findings
    scoreable_findings: List[SecurityFinding] = Field(default_factory=list)
    advisory_findings: List[SecurityFinding] = Field(default_factory=list)
    hidden_findings: List[SecurityFinding] = Field(default_factory=list)

    # Penalty breakdown
    total_penalty: float
    critical_penalty: float
    high_penalty: float
    medium_penalty: float
    low_penalty: float

    # OWASP ASI coverage
    owasp_asi_coverage: Dict[str, int] = Field(
        default_factory=dict,
        description="ASI01-ASI10 coverage map"
    )


# ============================================================================
# Phase 1 Combined Score
# ============================================================================

class Phase1Score(BaseModel):
    """Combined Phase 1 score: Static (50) + Security (50) = 100."""
    static: Phase1StaticScore
    security: Phase1SecurityScore

    total_score: float = Field(ge=0, le=100)
    grade: Grade
    publish_decision: PublishDecision

    auto_reject: bool
    auto_reject_reason: Optional[str] = None

    duration_seconds: float
    timestamp: str


# ============================================================================
# Base Penalty Weights
# ============================================================================

BASE_PENALTIES = {
    Severity.CRITICAL: 50.0,
    Severity.HIGH: 12.0,
    Severity.MEDIUM: 5.0,
    Severity.LOW: 2.0,
    Severity.INFO: 0.0,
}

# Confidence thresholds
SCORING_THRESHOLD = 0.5          # >= 0.5: contribute to score
ADVISORY_THRESHOLD = 0.3         # 0.3-0.49: display only
CRITICAL_REJECT_THRESHOLD = 0.7  # CRITICAL auto-reject requires >= 0.7
SECURITY_FLOOR = 25.0            # Score < 25/50 → auto-reject


# ============================================================================
# Grade Mapping Functions
# ============================================================================

def score_to_grade(score: float, max_score: float = 100) -> Grade:
    """Convert numeric score to letter grade per ADR."""
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


def grade_to_publish_decision(grade: Grade, auto_reject: bool) -> PublishDecision:
    """Map grade to publish decision per ADR."""
    if auto_reject:
        return PublishDecision.BLOCK

    if grade in (Grade.A, Grade.B):
        return PublishDecision.APPROVE
    elif grade == Grade.C:
        return PublishDecision.CONDITIONAL
    elif grade == Grade.D:
        return PublishDecision.REQUIRE_ACK
    else:  # Grade F
        return PublishDecision.BLOCK
