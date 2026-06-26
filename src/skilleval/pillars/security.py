"""
Pillar 2: Security

Detects security vulnerabilities, secrets, dangerous patterns.
"""

import time
import re
from pathlib import Path
from typing import List

from skilleval.models import (
    SecurityConfig,
    SecurityResult,
    Finding,
    Severity,
    Grade,
)
from skilleval.utils.logger import logger
from skilleval.utils.cve_scanner import CVEScanner
from skilleval.pillars.owasp_llm import OWASPLLMChecker
from skilleval.pillars.owasp_agentic import check_owasp_agentic
from skilleval.pillars.nist_ai_rmf import check_nist_ai_rmf
from skilleval.pillars.mlsec_top10 import check_mlsec_top10
from skilleval.utils.ast_analyzer import analyze_python_file
from skilleval.utils.llm_optimizer import analyze_llm_usage
from skilleval.utils.resource_analyzer import (
    analyze_resource_management,
    analyze_error_handling,
    analyze_performance,
)
from skilleval.utils.concurrency_analyzer import (
    analyze_concurrency,
    analyze_type_safety,
)


class SecurityPillar:
    """Security evaluation pillar."""

    # Secret patterns
    PATTERNS = {
        # Generic
        "api_key": r"['\"]?api[_-]?key['\"]?\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]",
        "password": r"['\"]?password['\"]?\s*[:=]\s*['\"][^'\"]{8,}['\"]",
        "private_key": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----",

        # Cloud providers
        "aws_key": r"AKIA[0-9A-Z]{16}",

        # LLM providers
        "openai_key": r"sk-[A-Za-z0-9]{48}",
        "anthropic_key": r"sk-ant-[A-Za-z0-9-]{95}",

        # Version control
        "github_token": r"gh[pousr]_[A-Za-z0-9]{36}",

        # SkillEval specific
        "generic_token": r"token_[A-Za-z0-9]{40}",
    }

    # Command injection patterns
    COMMAND_INJECTION = [
        r"subprocess\.call\([^)]*shell\s*=\s*True",
        r"os\.system\(",
        r"eval\(",
        r"exec\(",
        r"curl.*\|.*bash",
        r"wget.*\|.*sh",
    ]

    # SQL injection patterns (OWASP A03:2021 - Injection)
    SQL_INJECTION = [
        r"execute\(['\"].*%s.*['\"].*%",  # String formatting in SQL
        r"execute\(['\"].*\+.*['\"]",     # String concatenation
        r"\.format\(['\"].*SELECT.*FROM",  # Format strings in SQL
        r"f['\"]SELECT.*{.*}.*FROM",       # F-strings in SQL
    ]

    # XSS patterns (OWASP A03:2021 - Injection)
    XSS_PATTERNS = [
        r"innerHTML\s*=",                  # Direct innerHTML assignment
        r"document\.write\(",              # document.write
        r"\.html\([^)]*\+",                # jQuery .html() with concatenation
        r"dangerouslySetInnerHTML",        # React dangerous HTML
    ]

    # Path traversal (OWASP A01:2021 - Broken Access Control)
    PATH_TRAVERSAL = [
        r"open\([^)]*\+",                  # File open with concatenation
        r"Path\([^)]*\+",                  # Path with concatenation
        r"\.\./",                          # Directory traversal
    ]

    def __init__(self, config: SecurityConfig):
        self.config = config

    def run(self, skill_path: Path) -> SecurityResult:
        """
        Run security scan on a skill.

        Args:
            skill_path: Path to skill directory

        Returns:
            SecurityResult
        """
        start_time = time.time()

        findings: List[Finding] = []

        # Scan for secrets
        findings.extend(self._scan_secrets(skill_path))

        # Scan for command injection
        findings.extend(self._scan_command_injection(skill_path))

        # Scan for SQL injection (OWASP A03:2021)
        findings.extend(self._scan_sql_injection(skill_path))

        # Scan for XSS vulnerabilities (OWASP A03:2021)
        findings.extend(self._scan_xss(skill_path))

        # Scan for path traversal (OWASP A01:2021)
        findings.extend(self._scan_path_traversal(skill_path))

        # Scan for unapproved container registries
        findings.extend(self._scan_container_registries(skill_path))

        # Scan for CVEs in dependencies
        cve_findings = self._scan_cves(skill_path)
        findings.extend(cve_findings)

        # OWASP Top 10 for LLM checks
        owasp_llm_findings = self._scan_owasp_llm(skill_path)
        findings.extend(owasp_llm_findings)

        # AST-based deep analysis
        ast_findings = self._scan_with_ast(skill_path)
        findings.extend(ast_findings)

        # LLM usage optimization
        llm_opt_findings = self._scan_llm_optimization(skill_path)
        findings.extend(llm_opt_findings)

        # Resource management
        resource_findings = self._scan_resource_management(skill_path)
        findings.extend(resource_findings)

        # Error handling
        error_findings = self._scan_error_handling(skill_path)
        findings.extend(error_findings)

        # Performance anti-patterns
        perf_findings = self._scan_performance(skill_path)
        findings.extend(perf_findings)

        # Concurrency issues
        concurrency_findings = self._scan_concurrency(skill_path)
        findings.extend(concurrency_findings)

        # Type safety
        type_findings = self._scan_type_safety(skill_path)
        findings.extend(type_findings)

        # OWASP Agentic AI checks
        agentic_findings = self._scan_owasp_agentic(skill_path)
        findings.extend(agentic_findings)

        # NIST AI RMF checks
        nist_findings = self._scan_nist_ai_rmf(skill_path)
        findings.extend(nist_findings)

        # ML Security Top 10
        mlsec_findings = self._scan_mlsec_top10(skill_path)
        findings.extend(mlsec_findings)

        # Calculate score
        severity_weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }

        score = 100.0
        for finding in findings:
            weight = severity_weights.get(finding.severity, 5)
            score -= weight

        score = max(0, score)

        # Grade
        if score >= 90:
            grade = Grade.A
        elif score >= 75:
            grade = Grade.B
        elif score >= 60:
            grade = Grade.C
        elif score >= 45:
            grade = Grade.D
        else:
            grade = Grade.F

        # Categorize by severity
        by_severity = {}
        for finding in findings:
            sev = finding.severity.value
            by_severity[sev] = by_severity.get(sev, 0) + 1

        has_critical = any(f.severity == Severity.CRITICAL for f in findings)
        has_high = any(f.severity == Severity.HIGH for f in findings)

        duration = time.time() - start_time

        return SecurityResult(
            score=score,
            grade=grade,
            findings_total=len(findings),
            by_severity=by_severity,
            has_critical=has_critical,
            has_high=has_high,
            findings=findings,
            duration_seconds=duration,
        )

    def _scan_secrets(self, skill_path: Path) -> List[Finding]:
        """Scan for hardcoded secrets."""
        findings = []

        # Scan all text files
        for file_path in skill_path.rglob("*"):
            if not file_path.is_file():
                continue

            # Skip binary files
            if file_path.suffix in [".png", ".jpg", ".pdf", ".zip", ".tar", ".gz"]:
                continue

            try:
                content = file_path.read_text(errors="ignore")
            except Exception:
                continue

            for secret_type, pattern in self.PATTERNS.items():
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type=f"SECRET_{secret_type.upper()}",
                        severity=Severity.CRITICAL,
                        message=f"Potential {secret_type} found",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Remove hardcoded secrets. Use environment variables.",
                    ))

        return findings

    def _scan_command_injection(self, skill_path: Path) -> List[Finding]:
        """Scan for command injection vulnerabilities."""
        findings = []

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern in self.COMMAND_INJECTION:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1

                    # curl|bash is CRITICAL, others HIGH
                    if "curl" in pattern or "wget" in pattern:
                        severity = Severity.CRITICAL
                        remediation = "Never execute remote scripts directly. Review and execute manually."
                    else:
                        severity = Severity.HIGH
                        remediation = "Avoid shell=True. Use subprocess.run with list arguments."

                    findings.append(Finding(
                        type="COMMAND_INJECTION",
                        severity=severity,
                        message=f"Command injection risk: {match.group(0)}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation=remediation,
                    ))

        return findings

    def _scan_container_registries(self, skill_path: Path) -> List[Finding]:
        """Check for unapproved container registries."""
        findings = []

        # Look for container image references with registry/image:tag format
        # Matches: registry.io/image:tag or docker.io/library/image:tag or image:tag
        # Must have at least one "/" or ":" to be considered an image reference
        image_pattern = r"\b(FROM|image:|container:)\s+([a-zA-Z0-9._-]+[/:][a-zA-Z0-9._:/@-]+)"

        for file_path in skill_path.rglob("*"):
            if file_path.suffix not in [".md", ".yaml", ".yml", ".dockerfile", ".containerfile"]:
                continue

            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for match in re.finditer(image_pattern, content, re.IGNORECASE):
                image = match.group(2).strip()
                line_num = content[:match.start()].count("\n") + 1

                # Skip if it looks like markdown formatting or not an image
                if image.startswith('*') or image.endswith('**') or '**' in image:
                    continue
                if image.startswith('`') or image.endswith('`'):
                    continue

                # Check if approved
                is_approved = any(
                    image.startswith(reg) for reg in self.config.approved_registries
                )

                # Also approve well-known docker.io, gcr.io, etc (with warning)
                # Only flag truly suspicious or unknown registries
                known_registries = ['docker.io', 'gcr.io', 'ghcr.io', 'mcr.microsoft.com']
                is_known = any(image.startswith(reg) for reg in known_registries)

                if not is_approved and not is_known:
                    findings.append(Finding(
                        type="UNAPPROVED_CONTAINER",
                        severity=Severity.MEDIUM,
                        message=f"Container from unapproved registry: {image}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation=f"Use SkillEval certified images from {', '.join(self.config.approved_registries)}",
                    ))

        return findings

    def _scan_sql_injection(self, skill_path: Path) -> List[Finding]:
        """Scan for SQL injection vulnerabilities (OWASP A03:2021)."""
        findings = []

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern in self.SQL_INJECTION:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="SQL_INJECTION",
                        severity=Severity.HIGH,
                        message=f"Potential SQL injection: {match.group(0)[:50]}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Use parameterized queries or ORM. Never concatenate user input into SQL.",
                        owasp_id="A03:2021",
                    ))

        return findings

    def _scan_xss(self, skill_path: Path) -> List[Finding]:
        """Scan for XSS vulnerabilities (OWASP A03:2021)."""
        findings = []

        # Scan JS/TS files
        for file_path in skill_path.rglob("*"):
            if file_path.suffix not in [".js", ".jsx", ".ts", ".tsx", ".html"]:
                continue

            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern in self.XSS_PATTERNS:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="XSS",
                        severity=Severity.HIGH,
                        message=f"Potential XSS vulnerability: {match.group(0)}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Sanitize user input. Use textContent instead of innerHTML. Escape HTML entities.",
                        owasp_id="A03:2021",
                    ))

        return findings

    def _scan_path_traversal(self, skill_path: Path) -> List[Finding]:
        """Scan for path traversal vulnerabilities (OWASP A01:2021)."""
        findings = []

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern in self.PATH_TRAVERSAL:
                for match in re.finditer(pattern, content):
                    line_num = content[:match.start()].count("\n") + 1

                    # Skip if it's a relative import (from ..module)
                    if "from " in content[max(0, match.start()-10):match.start()]:
                        continue

                    findings.append(Finding(
                        type="PATH_TRAVERSAL",
                        severity=Severity.HIGH,
                        message=f"Potential path traversal: {match.group(0)}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Validate and sanitize file paths. Use os.path.normpath() and check against whitelist.",
                        owasp_id="A01:2021",
                    ))

        return findings

    def _scan_cves(self, skill_path: Path) -> List[Finding]:
        """Scan for CVEs in dependencies and container images."""
        findings = []

        # Scan Python dependencies
        cve_scanner = CVEScanner()
        python_cves = cve_scanner.scan_python_dependencies(skill_path)

        for cve in python_cves:
            # Map severity
            severity_map = {
                "CRITICAL": Severity.CRITICAL,
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
                "LOW": Severity.LOW,
            }
            severity = severity_map.get(cve["severity"], Severity.MEDIUM)

            findings.append(Finding(
                type="CVE",
                severity=severity,
                message=f"{cve['cve_id']}: {cve['package']}@{cve['version']} - {cve['description']}",
                file=cve["file"],
                line=None,
                remediation=f"Upgrade to {cve['fix_version']}" if cve['fix_version'] else "No fix available yet",
                owasp_id="A06:2021",  # Vulnerable and Outdated Components
            ))

        # Scan container images
        container_cves = cve_scanner.scan_container_images(skill_path)

        for cve in container_cves:
            severity_map = {
                "CRITICAL": Severity.CRITICAL,
                "HIGH": Severity.HIGH,
                "MEDIUM": Severity.MEDIUM,
                "LOW": Severity.LOW,
            }
            severity = severity_map.get(cve["severity"], Severity.MEDIUM)

            findings.append(Finding(
                type="CONTAINER_CVE",
                severity=severity,
                message=f"{cve['cve_id']}: {cve['package']}@{cve['version']} in {cve['image']}",
                file=None,
                line=None,
                remediation=f"Update base image or upgrade to {cve['fix_version']}" if cve['fix_version'] else "No fix available yet",
                owasp_id="A06:2021",
            ))

        return findings

    def _scan_owasp_llm(self, skill_path: Path) -> List[Finding]:
        """Scan for OWASP Top 10 for LLM vulnerabilities."""
        owasp_checker = OWASPLLMChecker()
        return owasp_checker.check_all(skill_path)

    def _scan_with_ast(self, skill_path: Path) -> List[Finding]:
        """Deep analysis using AST parsing."""
        findings = []

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                ast_findings = analyze_python_file(file_path, skill_path)
                findings.extend(ast_findings)
            except Exception:
                pass

        return findings

    def _scan_llm_optimization(self, skill_path: Path) -> List[Finding]:
        """Analyze LLM usage for optimization opportunities."""
        findings = []

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                llm_findings, _ = analyze_llm_usage(file_path, skill_path)
                findings.extend(llm_findings)
            except Exception:
                pass

        return findings

    def _scan_resource_management(self, skill_path: Path) -> List[Finding]:
        """Analyze resource management."""
        findings = []
        for file_path in skill_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    findings.extend(analyze_resource_management(file_path, skill_path))
                except Exception:
                    pass
        return findings

    def _scan_error_handling(self, skill_path: Path) -> List[Finding]:
        """Analyze error handling."""
        findings = []
        for file_path in skill_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    findings.extend(analyze_error_handling(file_path, skill_path))
                except Exception:
                    pass
        return findings

    def _scan_performance(self, skill_path: Path) -> List[Finding]:
        """Analyze performance anti-patterns."""
        findings = []
        for file_path in skill_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    findings.extend(analyze_performance(file_path, skill_path))
                except Exception:
                    pass
        return findings

    def _scan_concurrency(self, skill_path: Path) -> List[Finding]:
        """Analyze concurrency issues."""
        findings = []
        for file_path in skill_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    findings.extend(analyze_concurrency(file_path, skill_path))
                except Exception:
                    pass
        return findings

    def _scan_type_safety(self, skill_path: Path) -> List[Finding]:
        """Analyze type safety."""
        findings = []
        for file_path in skill_path.rglob("*.py"):
            if file_path.is_file():
                try:
                    findings.extend(analyze_type_safety(file_path, skill_path))
                except Exception:
                    pass
        return findings

    def _scan_owasp_agentic(self, skill_path: Path) -> List[Finding]:
        """Scan for OWASP Agentic AI vulnerabilities."""
        try:
            return check_owasp_agentic(skill_path, trace_data=None)
        except Exception as e:
            logger.warning(f"OWASP Agentic scan failed: {e}")
            return []

    def _scan_nist_ai_rmf(self, skill_path: Path) -> List[Finding]:
        """Scan for NIST AI RMF compliance."""
        try:
            return check_nist_ai_rmf(skill_path)
        except Exception as e:
            logger.warning(f"NIST AI RMF scan failed: {e}")
            return []

    def _scan_mlsec_top10(self, skill_path: Path) -> List[Finding]:
        """Scan for ML Security Top 10 vulnerabilities."""
        try:
            return check_mlsec_top10(skill_path)
        except Exception as e:
            logger.warning(f"ML Security scan failed: {e}")
            return []
