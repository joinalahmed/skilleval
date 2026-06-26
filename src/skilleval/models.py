"""
Core data models for SkillEval.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    """Finding severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"
    OK = "OK"
    WARNING = "WARNING"


class Grade(str, Enum):
    """Grade levels A-F."""
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    F = "F"
    NA = "N/A"


# ============================================================================
# Skill Models
# ============================================================================

class SkillFrontmatter(BaseModel):
    """SKILL.md frontmatter schema."""
    name: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    description: str = Field(..., min_length=10, max_length=2000)  # Increased from 500 to 2000
    license: Optional[str] = None
    compatibility: Optional[str] = None
    version: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Grader(BaseModel):
    """Deterministic grader definition."""
    model_config = {"protected_namespaces": ()}

    type: str  # file_exists, json_schema, content_match, etc.
    path: Optional[str] = None
    pattern: Optional[str] = None
    schema: Optional[Dict[str, Any]] = None
    command: Optional[List[str]] = None
    expected_code: Optional[int] = None
    expected_pattern: Optional[str] = None


class EvalCase(BaseModel):
    """Evaluation case definition from evals.json."""
    id: str
    prompt: str
    expected_output: str
    files: Optional[List[str]] = Field(default_factory=list)
    graders: Optional[List[Grader]] = Field(default_factory=list)
    assertions: Optional[List[str]] = Field(default_factory=list)

    @field_validator('id', mode='before')
    @classmethod
    def convert_id_to_string(cls, v):
        """Convert integer IDs to strings."""
        if isinstance(v, int):
            return str(v)
        return v

    @field_validator('expected_output', mode='before')
    @classmethod
    def convert_expected_output(cls, v):
        """Convert dict/object expected_output to JSON string."""
        if isinstance(v, dict):
            import json
            return json.dumps(v, indent=2)
        return v


class Skill(BaseModel):
    """Complete skill representation."""
    path: Path
    frontmatter: SkillFrontmatter
    body: str
    eval_cases: List[EvalCase] = Field(default_factory=list)
    has_evals: bool = False
    has_scripts: bool = False
    has_references: bool = False
    has_agents: bool = False


# ============================================================================
# Result Models
# ============================================================================

class Finding(BaseModel):
    """Security/OWASP finding."""
    type: str
    severity: Severity
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    remediation: Optional[str] = None
    owasp_id: Optional[str] = None


class StaticTestResult(BaseModel):
    """Static tests pillar result."""
    score: float = Field(ge=0, le=100)
    grade: Grade
    schema_valid: bool
    structure_valid: bool
    completeness: float = Field(ge=0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    duration_seconds: float


class SecurityResult(BaseModel):
    """Security pillar result."""
    score: float = Field(ge=0, le=100)
    grade: Grade
    findings_total: int
    by_severity: Dict[str, int]
    has_critical: bool
    has_high: bool
    findings: List[Finding]
    duration_seconds: float


class GraderResult(BaseModel):
    """Result from a single grader."""
    type: str
    passed: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class FunctionalResult(BaseModel):
    """Functional correctness result for one eval case."""
    case_id: str
    baseline_score: float = Field(ge=0, le=100)
    skill_score: float = Field(ge=0, le=100)
    improvement: float
    improvement_pct: float
    baseline_checks: List[GraderResult] = Field(default_factory=list)
    skill_checks: List[GraderResult] = Field(default_factory=list)


class SafetyCheck(BaseModel):
    """LLM safety check result."""
    check: str
    score: float = Field(ge=0, le=100)
    severity: Severity
    details: Dict[str, Any] = Field(default_factory=dict)


class OWASPCheck(BaseModel):
    """OWASP LLM check result."""
    score: float = Field(ge=0, le=100)
    grade: Grade
    findings_total: int
    by_severity: Dict[str, int]
    findings: List[Finding]


class HarnessResult(BaseModel):
    """Harness pillar result."""
    score: float = Field(ge=0, le=100)
    grade: Grade
    functional_score: float = Field(ge=0, le=100)
    safety_score: float = Field(ge=0, le=100)
    owasp_llm_score: float = Field(ge=0, le=100)
    functional_results: List[FunctionalResult] = Field(default_factory=list)
    safety_checks: List[SafetyCheck] = Field(default_factory=list)
    owasp_llm: Optional[OWASPCheck] = None
    duration_seconds: float


class FinalReport(BaseModel):
    """Final evaluation report."""
    skill_name: str
    skill_version: Optional[str] = None
    evaluation_date: datetime = Field(default_factory=datetime.now)
    framework_version: str = "0.1.0"

    final_score: float = Field(ge=0, le=100)
    grade: Grade
    recommendation: str

    pillar_scores: Dict[str, Any]
    total_duration_seconds: float

    metadata: Dict[str, Any] = Field(default_factory=dict)
    deterministic: bool = True
    run_to_run_variance: str = "0%"


class EvalResult(BaseModel):
    """Combined result from all pillars."""
    static_tests: Optional[StaticTestResult] = None
    security: Optional[SecurityResult] = None
    harness: Optional[HarnessResult] = None
    final_report: Optional[FinalReport] = None


# ============================================================================
# Configuration Models
# ============================================================================

class StaticTestsConfig(BaseModel):
    """Static tests configuration."""
    strict_mode: bool = True
    check_description_steps: bool = True
    min_description_length: int = 30
    min_body_length: int = 100


class SecurityConfig(BaseModel):
    """Security configuration."""
    min_score: int = 60
    fail_on_critical: bool = True
    fail_on_high: bool = False
    approved_registries: List[str] = Field(default_factory=lambda: [
        "docker.io",
        "docker.io",
        "quay.io",
    ])
    approved_licenses: List[str] = Field(default_factory=lambda: [
        "MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0", "LGPL-2.1", "MPL-2.0"
    ])


class HarnessConfig(BaseModel):
    """Harness configuration."""
    container_runtime: str = "podman"
    base_image: str = "docker.io/alpine/ubi-minimal:latest"
    selinux_enforcing: bool = True
    network_isolated: bool = True
    timeout_seconds: int = 300
    max_turns: int = 50
    max_tokens: int = 50000


class ScoringConfig(BaseModel):
    """Scoring configuration."""
    weights: Dict[str, float] = Field(default_factory=lambda: {
        "static_tests": 0.20,
        "security": 0.30,
        "harness": 0.50,
    })
    thresholds: Dict[str, int] = Field(default_factory=lambda: {
        "approve": 75,
        "conditional": 60,
        "reject": 60,
    })


class Config(BaseModel):
    """Main configuration."""
    framework_version: str = "0.1.0"
    deterministic: bool = True

    static_tests: StaticTestsConfig = Field(default_factory=StaticTestsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    harness: HarnessConfig = Field(default_factory=HarnessConfig)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)

    output_format: str = "json"  # json | html | both
    output_directory: str = "./reports"

    logging_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    logging_format: str = "pretty"  # pretty | json
