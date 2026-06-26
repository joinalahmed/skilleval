"""
Phase 1 Security Scorer (Layer 1 + Layer 2)

Implements the ADR's security analysis with confidence-weighted penalties.
Total: 50 points (deductive - start at 50, lose points per finding)

Security model:
  security_score = max(0, 50 - total_penalty)
  where total_penalty = sum(base_penalty × confidence) for scoreable findings

Confidence tiers:
  >= 0.7:       Full penalty weight; CRITICAL auto-reject
  0.5 - 0.69:   Full penalty weight; contributes to score
  0.3 - 0.49:   Advisory only (zero scoring impact)
  < 0.3:        Hidden (not shown)

Auto-reject conditions:
  - Any CRITICAL finding with confidence >= 0.7
  - Security score < 25/50 (50% floor)

Layer 1 (Built-in): 18 deterministic checks, zero dependencies
Layer 2 (SkillSpector): 64 patterns, AST, taint tracking (when available)
"""

import re
import hashlib
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from ..models_phase1 import (
    Phase1SecurityScore,
    SecurityFinding,
    SecurityLayerResult,
    Severity,
    Grade,
    BASE_PENALTIES,
    SCORING_THRESHOLD,
    ADVISORY_THRESHOLD,
    CRITICAL_REJECT_THRESHOLD,
    SECURITY_FLOOR,
    score_to_grade,
)


class SecurityScorer:
    """Scores security (Layer 1 built-in + Layer 2 SkillSpector) per ADR."""

    def __init__(self, skill_dir: Path):
        self.skill_dir = skill_dir
        self.skill_md = skill_dir / "SKILL.md"

    def score(self) -> Phase1SecurityScore:
        """Run security analysis and compute score."""
        start_time = datetime.now()

        # Layer 1: Built-in checks (always available)
        layer1_result = self._run_layer1()

        # Layer 2: SkillSpector (if available)
        layer2_result = self._run_layer2()

        # Deduplicate findings across layers
        all_findings = layer1_result.findings[:]
        if layer2_result:
            all_findings.extend(layer2_result.findings)

        deduplicated = self._deduplicate_findings(all_findings)

        # Separate by confidence tier
        scoreable = [f for f in deduplicated if f.confidence >= SCORING_THRESHOLD]
        advisory = [
            f for f in deduplicated
            if ADVISORY_THRESHOLD <= f.confidence < SCORING_THRESHOLD
        ]
        hidden = [f for f in deduplicated if f.confidence < ADVISORY_THRESHOLD]

        # Update is_scoreable and is_advisory flags
        for f in scoreable:
            f.is_scoreable = True
            f.is_advisory = False

        for f in advisory:
            f.is_scoreable = False
            f.is_advisory = True

        # Compute penalties
        total_penalty = sum(f.effective_penalty for f in scoreable)
        critical_penalty = sum(
            f.effective_penalty for f in scoreable if f.severity == Severity.CRITICAL
        )
        high_penalty = sum(
            f.effective_penalty for f in scoreable if f.severity == Severity.HIGH
        )
        medium_penalty = sum(
            f.effective_penalty for f in scoreable if f.severity == Severity.MEDIUM
        )
        low_penalty = sum(
            f.effective_penalty for f in scoreable if f.severity == Severity.LOW
        )

        # Compute score
        score = max(0.0, 50.0 - total_penalty)

        # Check auto-reject conditions
        has_critical_high_conf = any(
            f.severity == Severity.CRITICAL and f.confidence >= CRITICAL_REJECT_THRESHOLD
            for f in scoreable
        )
        below_security_floor = score < SECURITY_FLOOR
        auto_reject = has_critical_high_conf or below_security_floor

        # OWASP ASI coverage
        owasp_asi_coverage = self._compute_owasp_coverage(deduplicated)

        duration = (datetime.now() - start_time).total_seconds() * 1000  # ms

        grade = score_to_grade(score, max_score=50)

        return Phase1SecurityScore(
            score=score,
            grade=grade,
            has_critical_high_conf=has_critical_high_conf,
            below_security_floor=below_security_floor,
            auto_reject=auto_reject,
            layer1=layer1_result,
            layer2=layer2_result,
            scoreable_findings=scoreable,
            advisory_findings=advisory,
            hidden_findings=hidden,
            total_penalty=total_penalty,
            critical_penalty=critical_penalty,
            high_penalty=high_penalty,
            medium_penalty=medium_penalty,
            low_penalty=low_penalty,
            owasp_asi_coverage=owasp_asi_coverage,
        )

    # ========================================================================
    # Layer 1: Built-in Deterministic Checks (18 checks)
    # ========================================================================

    def _run_layer1(self) -> SecurityLayerResult:
        """Run all Layer 1 built-in security checks."""
        start_time = datetime.now()
        findings = []

        # Read all files
        all_files = self._get_all_files()

        for file_path in all_files:
            try:
                content = file_path.read_text(errors='ignore')
                relative_path = str(file_path.relative_to(self.skill_dir))

                # Run all Layer 1 checks
                findings.extend(self._l1_01_hardcoded_keys(content, relative_path))
                findings.extend(self._l1_02_high_entropy(content, relative_path))
                findings.extend(self._l1_03_zero_width_unicode(content, relative_path))
                findings.extend(self._l1_04_dangerous_yaml(content, relative_path))
                findings.extend(self._l1_05_data_exfiltration(content, relative_path))
                findings.extend(self._l1_06_credential_files(content, relative_path))
                findings.extend(self._l1_07_identity_modification(content, relative_path))
                findings.extend(self._l1_08_install_hooks(content, relative_path))
                findings.extend(self._l1_09_base64_payloads(content, relative_path))
                findings.extend(self._l1_10_insecure_http(content, relative_path))
                findings.extend(self._l1_11_escalation_language(content, relative_path))
                findings.extend(self._l1_12_unrestricted_filesystem(content, relative_path))
                findings.extend(self._l1_13_prompt_injection_markers(content, relative_path))
                findings.extend(self._l1_14_credentials_in_code(content, relative_path))
                findings.extend(self._l1_15_encoding_issues(file_path, relative_path))
                findings.extend(self._l1_16_binary_content(content, relative_path))
                findings.extend(self._l1_17_excessive_permissions(content, relative_path))
                findings.extend(self._l1_18_external_url_density(content, relative_path))

            except Exception as e:
                # Skip files that can't be read
                pass

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000

        return SecurityLayerResult(
            layer="Layer 1",
            scanner_name="built-in",
            scanner_version="1.0.0",
            findings=findings,
            duration_ms=duration_ms,
        )

    def _l1_01_hardcoded_keys(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-01: Hardcoded API keys."""
        findings = []
        patterns = {
            "sk-": (r'sk-[a-zA-Z0-9]{32,}', "OpenAI API key"),
            "ghp_": (r'ghp_[a-zA-Z0-9]{36,}', "GitHub personal access token"),
            "AKIA": (r'AKIA[0-9A-Z]{16}', "AWS access key"),
            "xox-": (r'xox[baprs]-[a-zA-Z0-9-]{10,}', "Slack token"),
            "glpat-": (r'glpat-[a-zA-Z0-9_-]{20,}', "GitLab PAT"),
            "rk_live_": (r'rk_live_[a-zA-Z0-9]{24,}', "Stripe live key"),
        }

        for prefix, (pattern, desc) in patterns.items():
            matches = re.finditer(pattern, content)
            for match in matches:
                # Check if in code block (lower confidence)
                in_code_block = self._is_in_code_block(content, match.start())
                confidence = 0.6 if in_code_block else 0.95

                findings.append(SecurityFinding(
                    finding_id=f"L1-01-{prefix}",
                    category="HC",  # Hardcoded Credentials
                    severity=Severity.CRITICAL,
                    confidence=confidence,
                    message=f"Hardcoded {desc} detected",
                    file=file,
                    line=self._get_line_number(content, match.start()),
                    pattern_matched=match.group(0)[:20] + "...",
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.CRITICAL],
                    effective_penalty=BASE_PENALTIES[Severity.CRITICAL] * confidence,
                    is_scoreable=confidence >= SCORING_THRESHOLD,
                    is_advisory=False,
                ))

        return findings

    def _l1_02_high_entropy(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-02: High-entropy strings (potential secrets)."""
        findings = []

        # Find strings outside code blocks
        words = re.findall(r'\b([a-zA-Z0-9+/=]{20,})\b', content)

        for word in words:
            if self._shannon_entropy(word) > 4.5:
                # Check context
                in_code_block = self._is_in_code_block(content, content.find(word))
                confidence = 0.4 if in_code_block else 0.7

                findings.append(SecurityFinding(
                    finding_id="L1-02",
                    category="HC",
                    severity=Severity.HIGH,
                    confidence=confidence,
                    message=f"High-entropy string detected (possible secret)",
                    file=file,
                    line=self._get_line_number(content, content.find(word)),
                    pattern_matched=word[:20] + "...",
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.HIGH],
                    effective_penalty=BASE_PENALTIES[Severity.HIGH] * confidence,
                    is_scoreable=confidence >= SCORING_THRESHOLD,
                    is_advisory=False,
                ))
                break  # Only report first high-entropy string per file

        return findings

    def _l1_03_zero_width_unicode(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-03: Zero-width Unicode (steganographic injection)."""
        findings = []
        pattern = r'[​‌‍⁠﻿]'

        if re.search(pattern, content):
            findings.append(SecurityFinding(
                finding_id="L1-03",
                category="PI",  # Prompt Injection
                severity=Severity.HIGH,
                confidence=0.9,
                message="Zero-width Unicode characters detected (steganography risk)",
                file=file,
                owasp_asi="ASI01",
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.HIGH],
                effective_penalty=BASE_PENALTIES[Severity.HIGH] * 0.9,
                is_scoreable=True,
                is_advisory=False,
            ))

        return findings

    def _l1_04_dangerous_yaml(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-04: Dangerous YAML tags."""
        findings = []
        patterns = [
            (r'!!python/object', "Python object deserialization"),
            (r'!!python/apply', "Python code execution via YAML"),
        ]

        for pattern, desc in patterns:
            if re.search(pattern, content):
                findings.append(SecurityFinding(
                    finding_id="L1-04",
                    category="CE",  # Code Execution
                    severity=Severity.CRITICAL,
                    confidence=0.95,
                    message=f"Dangerous YAML tag: {desc}",
                    file=file,
                    pattern_matched=pattern,
                    owasp_asi="ASI05",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.CRITICAL],
                    effective_penalty=BASE_PENALTIES[Severity.CRITICAL] * 0.95,
                    is_scoreable=True,
                    is_advisory=False,
                ))

        return findings

    def _l1_05_data_exfiltration(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-05: Data exfiltration patterns."""
        findings = []
        patterns = [
            (r'curl\s+-[dF]', "curl POST/upload"),
            (r'wget\s+--post', "wget POST"),
            (r'fetch\([^)]*method:\s*["\']POST["\']', "fetch POST"),
            (r'requests\.post\(', "requests POST"),
        ]

        for pattern, desc in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                findings.append(SecurityFinding(
                    finding_id="L1-05",
                    category="DE",  # Data Exfiltration
                    severity=Severity.HIGH,
                    confidence=0.7,
                    message=f"Data exfiltration pattern: {desc}",
                    file=file,
                    line=self._get_line_number(content, matches[0].start()),
                    pattern_matched=desc,
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.HIGH],
                    effective_penalty=BASE_PENALTIES[Severity.HIGH] * 0.7,
                    is_scoreable=True,
                    is_advisory=False,
                ))
                break  # One finding per file

        return findings

    def _l1_06_credential_files(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-06: References to credential files."""
        findings = []
        patterns = [
            r'\.env(?!\.\w)',
            r'\.ssh/',
            r'id_rsa',
            r'private_key',
            r'credentials\.json',
            r'\.aws/credentials',
        ]

        for pattern in patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                # Lower confidence if in documentation
                in_doc = any(
                    marker in content.lower()
                    for marker in ["example", "documentation", "readme"]
                )
                confidence = 0.4 if in_doc else 0.6

                findings.append(SecurityFinding(
                    finding_id="L1-06",
                    category="HC",
                    severity=Severity.MEDIUM,
                    confidence=confidence,
                    message=f"Credential file reference: {pattern}",
                    file=file,
                    line=self._get_line_number(content, matches[0].start()),
                    pattern_matched=pattern,
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                    effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * confidence,
                    is_scoreable=confidence >= SCORING_THRESHOLD,
                    is_advisory=confidence < SCORING_THRESHOLD,
                ))
                break

        return findings

    def _l1_07_identity_modification(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-07: Attempts to modify agent identity files."""
        findings = []
        identity_files = ["SOUL.md", "MEMORY.md", "AGENTS.md", "CLAUDE.md"]

        for identity in identity_files:
            pattern = rf'(write|edit|modify|update).*{re.escape(identity)}'
            if re.search(pattern, content, re.IGNORECASE):
                findings.append(SecurityFinding(
                    finding_id="L1-07",
                    category="RA",  # Rogue Agent
                    severity=Severity.HIGH,
                    confidence=0.8,
                    message=f"Attempt to modify agent identity file: {identity}",
                    file=file,
                    pattern_matched=identity,
                    owasp_asi="ASI10",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.HIGH],
                    effective_penalty=BASE_PENALTIES[Severity.HIGH] * 0.8,
                    is_scoreable=True,
                    is_advisory=False,
                ))
                break

        return findings

    def _l1_08_install_hooks(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-08: Install hooks in dependency files."""
        findings = []

        if "package.json" in file:
            if re.search(r'"(pre|post)install":', content):
                findings.append(SecurityFinding(
                    finding_id="L1-08",
                    category="SC",  # Supply Chain
                    severity=Severity.MEDIUM,
                    confidence=0.7,
                    message="Install hook in package.json (supply chain risk)",
                    file=file,
                    owasp_asi="ASI04",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                    effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * 0.7,
                    is_scoreable=True,
                    is_advisory=False,
                ))

        return findings

    def _l1_09_base64_payloads(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-09: Base64-encoded payloads in prose."""
        findings = []

        # Find base64 outside code blocks
        pattern = r'[A-Za-z0-9+/]{40,}={0,2}'
        matches = re.finditer(pattern, content)

        for match in matches:
            if self._is_in_code_block(content, match.start()):
                continue  # Skip code blocks

            findings.append(SecurityFinding(
                finding_id="L1-09",
                category="PI",
                severity=Severity.MEDIUM,
                confidence=0.5,
                message="Base64-encoded payload in prose (possible obfuscation)",
                file=file,
                line=self._get_line_number(content, match.start()),
                owasp_asi="ASI01",
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * 0.5,
                is_scoreable=True,
                is_advisory=False,
            ))
            break  # One per file

        return findings

    def _l1_10_insecure_http(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-10: HTTP URLs where HTTPS expected."""
        findings = []

        # Exclude localhost and 127.0.0.1
        pattern = r'http://(?!(?:localhost|127\.0\.0\.1))'
        matches = list(re.finditer(pattern, content, re.IGNORECASE))

        if matches and len(matches) > 2:  # More than 2 HTTP URLs
            findings.append(SecurityFinding(
                finding_id="L1-10",
                category="IT",  # Insecure Transport
                severity=Severity.LOW,
                confidence=0.6,
                message=f"Insecure HTTP URLs detected ({len(matches)} instances)",
                file=file,
                owasp_asi="ASI01",
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.LOW],
                effective_penalty=BASE_PENALTIES[Severity.LOW] * 0.6,
                is_scoreable=True,
                is_advisory=False,
            ))

        return findings

    def _l1_11_escalation_language(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-11: Escalation language (prompt injection)."""
        findings = []
        patterns = [
            "ignore previous instructions",
            "disregard system prompt",
            "forget what I said",
            "new instructions:",
        ]

        for pattern in patterns:
            if pattern in content.lower():
                findings.append(SecurityFinding(
                    finding_id="L1-11",
                    category="PI",
                    severity=Severity.HIGH,
                    confidence=0.85,
                    message=f"Prompt injection pattern: '{pattern}'",
                    file=file,
                    pattern_matched=pattern,
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.HIGH],
                    effective_penalty=BASE_PENALTIES[Severity.HIGH] * 0.85,
                    is_scoreable=True,
                    is_advisory=False,
                ))
                break  # One per file

        return findings

    def _l1_12_unrestricted_filesystem(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-12: Unrestricted file system operations."""
        findings = []
        patterns = [
            (r'rm\s+-rf\s+/', "recursive deletion from root"),
            (r'chmod\s+777', "overly permissive file permissions"),
            (r'sudo\s+rm', "privileged deletion"),
        ]

        for pattern, desc in patterns:
            if re.search(pattern, content):
                findings.append(SecurityFinding(
                    finding_id="L1-12",
                    category="EA",  # Excessive Agency
                    severity=Severity.MEDIUM,
                    confidence=0.7,
                    message=f"Unrestricted filesystem operation: {desc}",
                    file=file,
                    pattern_matched=pattern,
                    owasp_asi="ASI02",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                    effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * 0.7,
                    is_scoreable=True,
                    is_advisory=False,
                ))
                break

        return findings

    def _l1_13_prompt_injection_markers(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-13: Prompt injection markers (fake system tags)."""
        findings = []
        patterns = [
            r'<SYSTEM>',
            r'<IMPORTANT>',
            r'\[SYSTEM\]',
            r'\[ADMIN\]',
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.IGNORECASE):
                findings.append(SecurityFinding(
                    finding_id="L1-13",
                    category="PI",
                    severity=Severity.HIGH,
                    confidence=0.75,
                    message=f"Fake system tag/marker: {pattern}",
                    file=file,
                    pattern_matched=pattern,
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.HIGH],
                    effective_penalty=BASE_PENALTIES[Severity.HIGH] * 0.75,
                    is_scoreable=True,
                    is_advisory=False,
                ))
                break

        return findings

    def _l1_14_credentials_in_code(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-14: Credential patterns in code blocks."""
        findings = []

        # Extract code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', content)

        for block in code_blocks:
            # Look for password/key assignments
            pattern = r'(password|api[_-]?key|secret)\s*[:=]\s*["\']([^"\']{8,})["\']'
            matches = re.finditer(pattern, block, re.IGNORECASE)

            for match in matches:
                value = match.group(2)
                # Lower confidence if looks like example
                is_example = any(
                    marker in value.lower()
                    for marker in ["example", "your-", "my-", "test", "demo"]
                )
                confidence = 0.3 if is_example else 0.6

                findings.append(SecurityFinding(
                    finding_id="L1-14",
                    category="HC",
                    severity=Severity.MEDIUM,
                    confidence=confidence,
                    message=f"Credential in code block: {match.group(1)}",
                    file=file,
                    owasp_asi="ASI01",
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                    effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * confidence,
                    is_scoreable=confidence >= SCORING_THRESHOLD,
                    is_advisory=confidence < SCORING_THRESHOLD,
                ))
                break  # One per file

        return findings

    def _l1_15_encoding_issues(self, file_path: Path, file: str) -> List[SecurityFinding]:
        """L1-15: Non-UTF8 or BOM encoding."""
        findings = []

        try:
            content = file_path.read_bytes()

            # Check for BOM
            if content.startswith(b'\xef\xbb\xbf'):
                findings.append(SecurityFinding(
                    finding_id="L1-15",
                    category="ENC",  # Encoding
                    severity=Severity.LOW,
                    confidence=1.0,
                    message="UTF-8 BOM detected (may cause parsing issues)",
                    file=file,
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.LOW],
                    effective_penalty=BASE_PENALTIES[Severity.LOW] * 1.0,
                    is_scoreable=True,
                    is_advisory=False,
                ))

            # Try UTF-8 decode
            try:
                content.decode('utf-8')
            except UnicodeDecodeError:
                findings.append(SecurityFinding(
                    finding_id="L1-15",
                    category="ENC",
                    severity=Severity.LOW,
                    confidence=0.8,
                    message="Non-UTF8 encoding detected",
                    file=file,
                    layer="Layer 1",
                    base_penalty=BASE_PENALTIES[Severity.LOW],
                    effective_penalty=BASE_PENALTIES[Severity.LOW] * 0.8,
                    is_scoreable=True,
                    is_advisory=False,
                ))

        except Exception:
            pass

        return findings

    def _l1_16_binary_content(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-16: Binary content in text files."""
        findings = []

        # Check for null bytes
        if '\x00' in content:
            findings.append(SecurityFinding(
                finding_id="L1-16",
                category="BIN",  # Binary content
                severity=Severity.MEDIUM,
                confidence=0.9,
                message="Null bytes detected (binary content in text file)",
                file=file,
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.MEDIUM],
                effective_penalty=BASE_PENALTIES[Severity.MEDIUM] * 0.9,
                is_scoreable=True,
                is_advisory=False,
            ))

        return findings

    def _l1_17_excessive_permissions(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-17: Excessive permissions language."""
        findings = []
        patterns = [
            "full access",
            "all permissions",
            "admin rights",
            "root access",
            "unrestricted",
        ]

        count = sum(1 for p in patterns if p in content.lower())
        if count >= 3:
            findings.append(SecurityFinding(
                finding_id="L1-17",
                category="EA",
                severity=Severity.LOW,
                confidence=0.5,
                message=f"Excessive permissions language ({count} instances)",
                file=file,
                owasp_asi="ASI02",
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.LOW],
                effective_penalty=BASE_PENALTIES[Severity.LOW] * 0.5,
                is_scoreable=True,
                is_advisory=False,
            ))

        return findings

    def _l1_18_external_url_density(self, content: str, file: str) -> List[SecurityFinding]:
        """L1-18: High external URL density."""
        findings = []

        # Extract unique domains
        urls = re.findall(r'https?://([^/\s]+)', content)
        unique_domains = set(urls)

        if len(unique_domains) > 5:
            findings.append(SecurityFinding(
                finding_id="L1-18",
                category="DE",
                severity=Severity.LOW,
                confidence=0.4,
                message=f"High external URL density ({len(unique_domains)} domains)",
                file=file,
                owasp_asi="ASI01",
                layer="Layer 1",
                base_penalty=BASE_PENALTIES[Severity.LOW],
                effective_penalty=BASE_PENALTIES[Severity.LOW] * 0.4,
                is_scoreable=False,  # conf < 0.5
                is_advisory=True,
            ))

        return findings

    # ========================================================================
    # Layer 2: SkillSpector (optional, when available)
    # ========================================================================

    def _run_layer2(self) -> Optional[SecurityLayerResult]:
        """Run SkillSpector if available."""
        try:
            # Try to import SkillSpector
            # For now, return None (not implemented)
            # This would be: from skillspector.graph import graph
            return None
        except ImportError:
            return None

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_all_files(self) -> List[Path]:
        """Get all text files in skill directory."""
        files = []
        for ext in ['.md', '.py', '.sh', '.json', '.yaml', '.yml', '.txt']:
            files.extend(self.skill_dir.rglob(f'*{ext}'))
        return files

    def _is_in_code_block(self, content: str, pos: int) -> bool:
        """Check if position is inside a code block (```)."""
        before = content[:pos]
        triple_backticks = before.count('```')
        return triple_backticks % 2 == 1  # Odd count = inside block

    def _get_line_number(self, content: str, pos: int) -> int:
        """Get line number for position in content."""
        return content[:pos].count('\n') + 1

    def _shannon_entropy(self, data: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not data:
            return 0.0

        entropy = 0.0
        for x in range(256):
            p_x = data.count(chr(x)) / len(data)
            if p_x > 0:
                entropy += - p_x * (p_x ** 0.5)  # Simplified

        return entropy

    def _deduplicate_findings(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """
        Deduplicate findings across layers.

        Rule: If Layer 1 and Layer 2 fire on same file+line (within 3 lines),
        keep the higher-confidence finding.
        """
        if not findings:
            return []

        # Group by file + category
        by_location = {}
        for f in findings:
            key = (f.file, f.category, (f.line or 0) // 3)  # Group by 3-line window
            if key not in by_location:
                by_location[key] = []
            by_location[key].append(f)

        # Keep highest confidence per group
        deduplicated = []
        for group in by_location.values():
            if len(group) == 1:
                deduplicated.append(group[0])
            else:
                # Multiple findings in same location - keep highest confidence
                best = max(group, key=lambda f: f.confidence)
                deduplicated.append(best)

        return deduplicated

    def _compute_owasp_coverage(self, findings: List[SecurityFinding]) -> Dict[str, int]:
        """Compute OWASP ASI coverage from findings."""
        coverage = {}
        for f in findings:
            if f.owasp_asi:
                coverage[f.owasp_asi] = coverage.get(f.owasp_asi, 0) + 1
        return coverage
