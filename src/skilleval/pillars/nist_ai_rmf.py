"""
NIST AI Risk Management Framework (AI RMF) Checks

Based on: NIST AI 600-1 (2023)
Focus: Trustworthy AI characteristics for production systems.
"""

import re
from pathlib import Path
from typing import List

from skilleval.models import Finding, Severity


class NISTAIRMFChecker:
    """
    NIST AI Risk Management Framework checks.

    Four core functions:
    1. GOVERN - Policies and oversight
    2. MAP - Context and risk identification
    3. MEASURE - Assessment and metrics
    4. MANAGE - Risk response and monitoring
    """

    def check_all(self, skill_path: Path) -> List[Finding]:
        """Run all NIST AI RMF checks."""
        findings = []

        findings.extend(self._check_transparency(skill_path))
        findings.extend(self._check_explainability(skill_path))
        findings.extend(self._check_fairness(skill_path))
        findings.extend(self._check_accountability(skill_path))
        findings.extend(self._check_reliability(skill_path))
        findings.extend(self._check_safety(skill_path))
        findings.extend(self._check_privacy(skill_path))

        return findings

    def _check_transparency(self, skill_path: Path) -> List[Finding]:
        """
        Transparency: System behavior should be understandable.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check for black-box AI usage without explanation
                has_ai_call = bool(re.search(r'\.generate\(|\.chat\(|\.predict\(', content))
                has_explanation = bool(re.search(r'explain|reasoning|rationale|why', content, re.IGNORECASE))

                if has_ai_call and not has_explanation:
                    findings.append(Finding(
                        type="NIST_NO_TRANSPARENCY",
                        severity=Severity.MEDIUM,
                        message="AI calls without explanation/reasoning capture",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Capture and expose AI reasoning for transparency",
                    ))
            except Exception:
                pass

        return findings

    def _check_explainability(self, skill_path: Path) -> List[Finding]:
        """
        Explainability: Decisions should have traceable logic.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check for decision-making without logging rationale
                patterns = [
                    (r'if.*decision', 'Decision without rationale'),
                    (r'if.*score\s*>', 'Threshold decision without explanation'),
                    (r'if.*classify', 'Classification without explanation'),
                ]

                for pattern, desc in patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        # Check if there's logging nearby
                        has_logging = bool(re.search(r'log|print.*because|reason', content, re.IGNORECASE))

                        if not has_logging:
                            findings.append(Finding(
                                type="NIST_NO_EXPLAINABILITY",
                                severity=Severity.LOW,
                                message=f"Decision-making without explainability: {desc}",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Log decision rationale for explainability",
                            ))
                        break
            except Exception:
                pass

        return findings

    def _check_fairness(self, skill_path: Path) -> List[Finding]:
        """
        Fairness: No bias in data or algorithms.
        """
        findings = []

        # Keywords indicating potential bias issues
        bias_keywords = [
            'race', 'gender', 'age', 'religion', 'nationality',
            'ethnicity', 'disability', 'sexual_orientation'
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for keyword in bias_keywords:
                    if re.search(rf'\b{keyword}\b', content, re.IGNORECASE):
                        # Check for fairness considerations
                        has_fairness = bool(re.search(
                            r'(fair|bias|discrimination|equity|protected)',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_fairness:
                            findings.append(Finding(
                                type="NIST_FAIRNESS_CONCERN",
                                severity=Severity.MEDIUM,
                                message=f"Sensitive attribute '{keyword}' without fairness checks",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Add bias detection and mitigation for sensitive attributes",
                            ))
                        break
            except Exception:
                pass

        return findings

    def _check_accountability(self, skill_path: Path) -> List[Finding]:
        """
        Accountability: Clear responsibility and audit trails.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # AI decisions without audit trail
                has_decision = bool(re.search(r'(decide|classify|recommend|approve|reject)', content, re.IGNORECASE))
                has_audit = bool(re.search(r'(audit|trail|log|record|track)', content, re.IGNORECASE))

                if has_decision and not has_audit:
                    findings.append(Finding(
                        type="NIST_NO_ACCOUNTABILITY",
                        severity=Severity.MEDIUM,
                        message="Decision-making without audit trail",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add audit logging for accountability",
                    ))
            except Exception:
                pass

        return findings

    def _check_reliability(self, skill_path: Path) -> List[Finding]:
        """
        Reliability: Consistent and dependable performance.
        """
        findings = []

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # AI calls without error handling
                ai_call_pattern = r'(\.generate|\.chat|\.predict)\('
                if re.search(ai_call_pattern, content):
                    # Check for try/except around AI calls
                    has_error_handling = bool(re.search(r'try:.*\.generate|try:.*\.chat', content, re.DOTALL))

                    if not has_error_handling:
                        findings.append(Finding(
                            type="NIST_NO_RELIABILITY",
                            severity=Severity.MEDIUM,
                            message="AI calls without error handling for reliability",
                            file=str(file_path.relative_to(skill_path)),
                            line=None,
                            remediation="Add try/except around AI calls with fallback logic",
                        ))
            except Exception:
                pass

        return findings

    def _check_safety(self, skill_path: Path) -> List[Finding]:
        """
        Safety: Protection from harm.
        """
        findings = []

        # Unsafe operations without validation
        unsafe_ops = [
            (r'subprocess\.', 'subprocess execution'),
            (r'os\.system', 'OS command execution'),
            (r'eval\(', 'eval usage'),
            (r'exec\(', 'exec usage'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for pattern, desc in unsafe_ops:
                    if re.search(pattern, content):
                        # Check for safety validation
                        has_validation = bool(re.search(
                            r'(validate|sanitize|check|verify|safe)',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_validation:
                            findings.append(Finding(
                                type="NIST_SAFETY_CONCERN",
                                severity=Severity.HIGH,
                                message=f"Unsafe operation ({desc}) without validation",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Add input validation for safety",
                            ))
                        break
            except Exception:
                pass

        return findings

    def _check_privacy(self, skill_path: Path) -> List[Finding]:
        """
        Privacy: Protection of user data.
        """
        findings = []

        # PII keywords
        pii_keywords = [
            'ssn', 'social_security', 'credit_card', 'password',
            'email', 'phone', 'address', 'birthdate', 'ip_address'
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for keyword in pii_keywords:
                    if re.search(rf'\b{keyword}\b', content, re.IGNORECASE):
                        # Check for privacy protections
                        has_privacy = bool(re.search(
                            r'(encrypt|hash|redact|anonymize|mask)',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_privacy:
                            findings.append(Finding(
                                type="NIST_PRIVACY_CONCERN",
                                severity=Severity.HIGH,
                                message=f"PII '{keyword}' without privacy protection",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Encrypt, hash, or redact PII data",
                            ))
                        break
            except Exception:
                pass

        return findings


def check_nist_ai_rmf(skill_path: Path) -> List[Finding]:
    """
    Main entry point for NIST AI RMF checks.

    Args:
        skill_path: Path to skill directory

    Returns:
        List of findings
    """
    checker = NISTAIRMFChecker()
    return checker.check_all(skill_path)
