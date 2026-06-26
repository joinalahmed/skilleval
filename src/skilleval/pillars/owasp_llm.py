"""
OWASP Top 10 for LLM Applications checks.

Reference: https://owasp.org/www-project-top-10-for-large-language-model-applications/
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any

from skilleval.models import Finding, Severity


class OWASPLLMChecker:
    """OWASP Top 10 for LLM Applications security checks."""

    def __init__(self):
        """Initialize OWASP LLM checker."""
        pass

    def check_all(self, skill_path: Path, trace_data: Dict[str, Any] = None) -> List[Finding]:
        """
        Run all OWASP LLM Top 10 checks.

        Args:
            skill_path: Path to skill directory
            trace_data: Optional trace data from execution

        Returns:
            List of findings
        """
        findings = []

        # Static analysis checks
        findings.extend(self.check_llm01_prompt_injection(skill_path))
        findings.extend(self.check_llm02_insecure_output(skill_path))
        findings.extend(self.check_llm04_model_dos(skill_path))
        findings.extend(self.check_llm05_supply_chain(skill_path))
        findings.extend(self.check_llm06_sensitive_disclosure(skill_path))
        findings.extend(self.check_llm07_insecure_plugin(skill_path))
        findings.extend(self.check_llm08_excessive_agency(skill_path))

        # Trace-based checks (if trace available)
        if trace_data:
            findings.extend(self.check_llm09_overreliance(trace_data))
            findings.extend(self.check_llm04_dos_runtime(trace_data))

        return findings

    def check_llm01_prompt_injection(self, skill_path: Path) -> List[Finding]:
        """
        LLM01: Prompt Injection

        Detects potential prompt injection vulnerabilities where user input
        is directly concatenated into prompts without sanitization.
        """
        findings = []

        # Patterns that indicate prompt injection risk
        patterns = [
            # Direct string concatenation in prompts
            (r'prompt\s*=\s*["\'].*["\'].*\+.*user', 'Direct user input concatenation into prompt'),
            (r'prompt\s*=\s*f["\'].*{.*user.*}', 'F-string with user input in prompt'),
            (r'\.format\(.*user.*\)', 'String format with user input'),

            # System prompts that include user data
            (r'system.*=.*\+.*user', 'User input in system prompt'),
            (r'instructions.*=.*user', 'User input in instructions'),

            # No input validation
            (r'user_input\s*=\s*input\(\)', 'Unvalidated user input'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern, description in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="LLM01_PROMPT_INJECTION",
                        severity=Severity.HIGH,
                        message=f"Potential prompt injection: {description}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Sanitize user input. Use parameterized prompts. Implement input validation.",
                        owasp_id="LLM01",
                    ))

        return findings

    def check_llm02_insecure_output(self, skill_path: Path) -> List[Finding]:
        """
        LLM02: Insecure Output Handling

        Detects when LLM outputs are used unsafely (e.g., in SQL, shell, eval).
        """
        findings = []

        patterns = [
            # LLM output used in dangerous contexts
            (r'response.*\).*execute\(', 'LLM output used in SQL execute'),
            (r'response.*\).*os\.system', 'LLM output used in os.system'),
            (r'response.*\).*subprocess.*shell\s*=\s*True', 'LLM output used in shell command'),
            (r'eval\(.*response', 'LLM output used in eval()'),
            (r'exec\(.*response', 'LLM output used in exec()'),

            # Direct execution of LLM suggestions
            (r'\.content.*execute', 'LLM content executed directly'),
            (r'\.text.*eval', 'LLM text evaluated directly'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern, description in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="LLM02_INSECURE_OUTPUT",
                        severity=Severity.CRITICAL,
                        message=f"Insecure output handling: {description}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Never execute LLM output directly. Validate and sanitize all LLM responses.",
                        owasp_id="LLM02",
                    ))

        return findings

    def check_llm04_model_dos(self, skill_path: Path) -> List[Finding]:
        """
        LLM04: Model Denial of Service

        Detects patterns that could cause resource exhaustion.
        """
        findings = []

        patterns = [
            # Unbounded loops calling LLM
            (r'while\s+True:.*(?:chat|complete|generate)', 'Infinite loop with LLM calls'),
            (r'for.*in.*range\([0-9]{4,}\).*(?:chat|complete)', 'Large loop with LLM calls'),

            # No rate limiting
            (r'(?:chat|complete|generate).*(?!.*sleep|.*limit|.*throttle)', 'No rate limiting on LLM calls'),

            # No timeout
            (r'\.chat\((?!.*timeout)', 'No timeout on LLM call'),

            # Unbounded context accumulation
            (r'messages\.append\((?!.*if len)', 'Unbounded message history'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            # Check for while True with LLM calls
            if re.search(r'while\s+True:', content, re.IGNORECASE):
                if re.search(r'(?:chat|complete|generate|invoke)', content, re.IGNORECASE):
                    line_num = content.find('while True')
                    line_num = content[:line_num].count("\n") + 1

                    findings.append(Finding(
                        type="LLM04_MODEL_DOS",
                        severity=Severity.HIGH,
                        message="Unbounded loop with LLM calls can cause DoS",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Add max iterations limit. Implement rate limiting and timeouts.",
                        owasp_id="LLM04",
                    ))

            # Check for large loops
            for match in re.finditer(r'for.*in.*range\(([0-9]+)\)', content):
                count = int(match.group(1))
                if count > 100:
                    # Check if loop contains LLM calls
                    loop_start = match.end()
                    # Simple heuristic: check next 500 chars
                    loop_body = content[loop_start:loop_start+500]
                    if re.search(r'(?:chat|complete|generate|invoke)', loop_body, re.IGNORECASE):
                        line_num = content[:match.start()].count("\n") + 1

                        findings.append(Finding(
                            type="LLM04_MODEL_DOS",
                            severity=Severity.MEDIUM,
                            message=f"Large loop ({count} iterations) with LLM calls",
                            file=str(file_path.relative_to(skill_path)),
                            line=line_num,
                            remediation="Limit iterations. Add rate limiting. Consider batching.",
                            owasp_id="LLM04",
                        ))

        return findings

    def check_llm04_dos_runtime(self, trace_data: Dict[str, Any]) -> List[Finding]:
        """
        LLM04: Model DoS (Runtime)

        Detects actual DoS patterns from trace data.
        """
        findings = []

        # Check token usage
        total_tokens = trace_data.get('total_tokens', 0)
        if total_tokens > 100000:
            findings.append(Finding(
                type="LLM04_MODEL_DOS",
                severity=Severity.HIGH,
                message=f"Excessive token usage: {total_tokens} tokens",
                file=None,
                line=None,
                remediation="Implement token budgets. Add early stopping conditions.",
                owasp_id="LLM04",
            ))

        # Check turn count
        turn_count = trace_data.get('turn_count', 0)
        if turn_count > 50:
            findings.append(Finding(
                type="LLM04_MODEL_DOS",
                severity=Severity.MEDIUM,
                message=f"Excessive turns: {turn_count} turns",
                file=None,
                line=None,
                remediation="Add max turns limit. Detect infinite loops.",
                owasp_id="LLM04",
            ))

        return findings

    def check_llm05_supply_chain(self, skill_path: Path) -> List[Finding]:
        """
        LLM05: Supply-Chain Vulnerabilities

        Detects third-party model/plugin risks.
        """
        findings = []

        # Check for model downloads from untrusted sources
        patterns = [
            (r'from_pretrained\(["\'](?!openai|anthropic|huggingface)', 'Model from untrusted source'),
            (r'download.*model.*http://(?!huggingface)', 'Model download over HTTP'),
            (r'torch\.load\((?!.*verify)', 'Unverified model loading'),
            (r'pickle\.load\((?!.*verify)', 'Unverified pickle loading'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern, description in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="LLM05_SUPPLY_CHAIN",
                        severity=Severity.HIGH,
                        message=f"Supply chain risk: {description}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Use trusted model sources. Verify model checksums. Use official APIs.",
                        owasp_id="LLM05",
                    ))

        return findings

    def check_llm06_sensitive_disclosure(self, skill_path: Path) -> List[Finding]:
        """
        LLM06: Sensitive Information Disclosure

        Detects patterns that could leak sensitive data to LLM.
        """
        findings = []

        patterns = [
            # Sending credentials to LLM
            (r'(?:password|api_key|token|secret).*(?:chat|prompt|message)', 'Credentials sent to LLM'),
            (r'(?:chat|prompt).*(?:password|api_key|token)', 'Credentials in prompt'),

            # PII in prompts
            (r'(?:ssn|credit_card|email|phone).*(?:chat|prompt)', 'PII sent to LLM'),

            # Database content in prompts
            (r'SELECT.*FROM.*(?:chat|prompt)', 'Database query results to LLM'),

            # Environment variables in prompts
            (r'os\.environ.*(?:chat|prompt)', 'Environment variables to LLM'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern, description in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="LLM06_SENSITIVE_DISCLOSURE",
                        severity=Severity.CRITICAL,
                        message=f"Sensitive data disclosure: {description}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Never send credentials/PII to LLM. Redact sensitive data. Use data minimization.",
                        owasp_id="LLM06",
                    ))

        return findings

    def check_llm07_insecure_plugin(self, skill_path: Path) -> List[Finding]:
        """
        LLM07: Insecure Plugin Design

        Detects insecure tool/plugin implementations.
        """
        findings = []

        # Check SKILL.md for tool definitions
        skill_md = skill_path / "SKILL.md"
        if skill_md.exists():
            try:
                content = skill_md.read_text()

                # Check for dangerous tool permissions
                dangerous_patterns = [
                    (r'```xml.*<tool>.*shell.*</tool>', 'Tool with shell access'),
                    (r'```xml.*<tool>.*exec.*</tool>', 'Tool with exec permission'),
                    (r'```xml.*<tool>.*file_write.*</tool>', 'Tool with unrestricted file write'),
                ]

                for pattern, description in dangerous_patterns:
                    if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                        findings.append(Finding(
                            type="LLM07_INSECURE_PLUGIN",
                            severity=Severity.HIGH,
                            message=f"Insecure plugin design: {description}",
                            file="SKILL.md",
                            line=None,
                            remediation="Limit plugin permissions. Implement authorization checks. Use allowlists.",
                            owasp_id="LLM07",
                        ))

            except Exception:
                pass

        # Check Python code for unsafe tool implementations
        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            # Tool without input validation
            if 'def tool_' in content or '@tool' in content:
                if not re.search(r'(?:validate|check|assert|raise).*input', content, re.IGNORECASE):
                    line_num = content.find('def tool_')
                    if line_num == -1:
                        line_num = content.find('@tool')
                    line_num = content[:line_num].count("\n") + 1

                    findings.append(Finding(
                        type="LLM07_INSECURE_PLUGIN",
                        severity=Severity.MEDIUM,
                        message="Tool implementation missing input validation",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Add input validation. Implement allowlists. Check authorization.",
                        owasp_id="LLM07",
                    ))

        return findings

    def check_llm08_excessive_agency(self, skill_path: Path) -> List[Finding]:
        """
        LLM08: Excessive Agency

        Detects when skills have too many permissions or autonomous capabilities.
        """
        findings = []

        # Check for autonomous loops
        autonomous_patterns = [
            (r'while.*(?:chat|complete).*(?!user)', 'Autonomous loop without user confirmation'),
            (r'agent.*autonomous.*True', 'Autonomous agent mode enabled'),
            (r'max_iterations\s*=\s*[0-9]{3,}', 'Very high max iterations'),
        ]

        for file_path in skill_path.rglob("*.py"):
            if not file_path.is_file():
                continue

            try:
                content = file_path.read_text()
            except Exception:
                continue

            for pattern, description in autonomous_patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    line_num = content[:match.start()].count("\n") + 1

                    findings.append(Finding(
                        type="LLM08_EXCESSIVE_AGENCY",
                        severity=Severity.HIGH,
                        message=f"Excessive agency: {description}",
                        file=str(file_path.relative_to(skill_path)),
                        line=line_num,
                        remediation="Require user confirmation for autonomous actions. Limit scope. Add human-in-the-loop.",
                        owasp_id="LLM08",
                    ))

            # Check for dangerous permissions
            dangerous_actions = ['delete', 'remove', 'drop', 'truncate', 'destroy']
            for action in dangerous_actions:
                if re.search(rf'def.*{action}.*\((?!.*confirm)', content, re.IGNORECASE):
                    line_num = content.lower().find(f'def {action}')
                    if line_num != -1:
                        line_num = content[:line_num].count("\n") + 1

                        findings.append(Finding(
                            type="LLM08_EXCESSIVE_AGENCY",
                            severity=Severity.MEDIUM,
                            message=f"Destructive action '{action}' without confirmation",
                            file=str(file_path.relative_to(skill_path)),
                            line=line_num,
                            remediation="Add user confirmation for destructive actions. Implement undo/rollback.",
                            owasp_id="LLM08",
                        ))

        return findings

    def check_llm09_overreliance(self, trace_data: Dict[str, Any]) -> List[Finding]:
        """
        LLM09: Overreliance

        Detects patterns of over-trusting LLM outputs without verification.
        """
        findings = []

        # Check if outputs are verified
        unverified_executions = trace_data.get('unverified_executions', 0)
        total_executions = trace_data.get('total_executions', 1)

        if unverified_executions > 0:
            ratio = unverified_executions / total_executions
            if ratio > 0.5:
                findings.append(Finding(
                    type="LLM09_OVERRELIANCE",
                    severity=Severity.MEDIUM,
                    message=f"{int(ratio*100)}% of executions unverified - overreliance on LLM",
                    file=None,
                    line=None,
                    remediation="Implement verification steps. Add sanity checks. Validate LLM outputs.",
                    owasp_id="LLM09",
                ))

        # Check for hallucination markers
        hallucinations = trace_data.get('hallucination_markers', [])
        if len(hallucinations) > 3:
            findings.append(Finding(
                type="LLM09_OVERRELIANCE",
                severity=Severity.HIGH,
                message=f"{len(hallucinations)} hallucination markers detected",
                file=None,
                line=None,
                remediation="Add fact-checking. Verify file paths. Validate function calls.",
                owasp_id="LLM09",
            ))

        return findings

    def calculate_owasp_score(self, findings: List[Finding]) -> float:
        """
        Calculate overall OWASP LLM security score.

        Args:
            findings: List of OWASP findings

        Returns:
            Score 0-100 (100 = no issues)
        """
        score = 100.0

        severity_weights = {
            Severity.CRITICAL: 15,
            Severity.HIGH: 10,
            Severity.MEDIUM: 5,
            Severity.LOW: 2,
        }

        for finding in findings:
            weight = severity_weights.get(finding.severity, 5)
            score -= weight

        return max(0, score)
