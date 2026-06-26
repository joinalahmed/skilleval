"""
OWASP Top 10 for Agentic Applications (2024)

Based on: https://owasp.org/www-project-top-10-for-large-language-model-applications/
Focus: Autonomous agents, multi-step workflows, tool use.
"""

import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from skilleval.models import Finding, Severity


class OWASPAgenticChecker:
    """
    OWASP Top 10 for Agentic AI Applications.

    Key differences from LLM apps:
    - Agents have autonomy (planning, decision-making)
    - Multi-turn interactions
    - Tool/function calling
    - State management
    - Chain-of-thought reasoning
    """

    def __init__(self):
        pass

    def check_all(self, skill_path: Path, trace_data: Optional[Dict] = None) -> List[Finding]:
        """Run all OWASP Agentic checks."""
        findings = []

        findings.extend(self._check_agent01_unbounded_autonomy(skill_path, trace_data))
        findings.extend(self._check_agent02_tool_access_control(skill_path))
        findings.extend(self._check_agent03_planning_injection(skill_path))
        findings.extend(self._check_agent04_tool_hallucination(skill_path, trace_data))
        findings.extend(self._check_agent05_state_poisoning(skill_path))
        findings.extend(self._check_agent06_recursive_loops(skill_path))
        findings.extend(self._check_agent07_credential_leakage(skill_path))
        findings.extend(self._check_agent08_context_overflow(skill_path, trace_data))
        findings.extend(self._check_agent09_action_confirmation(skill_path))
        findings.extend(self._check_agent10_audit_logging(skill_path))

        return findings

    def _check_agent01_unbounded_autonomy(
        self, skill_path: Path, trace_data: Optional[Dict]
    ) -> List[Finding]:
        """
        AGENT-01: Unbounded Autonomy

        Risk: Agent acts without limits (infinite loops, excessive tool calls, runaway costs).
        """
        findings = []

        # Pattern 1: No turn limits
        patterns = [
            (r'while\s+True:', 'Infinite loop without turn limits'),
            (r'for\s+_\s+in\s+range\(\d{3,}\):', 'Very large iteration count'),
            (r'max_iterations\s*=\s*None', 'No iteration limit'),
            (r'max_turns\s*=\s*None', 'No turn limit'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="AGENT01_UNBOUNDED_AUTONOMY",
                            severity=Severity.HIGH,
                            message=f"Unbounded autonomy: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Set max_turns, max_iterations, timeout, or budget limits",
                        ))
            except Exception:
                pass

        # Pattern 2: No cost limits
        cost_patterns = [
            (r'def.*call.*llm', 'LLM call without cost tracking'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check if has LLM calls but no budget/cost tracking
                has_llm_calls = bool(re.search(r'\.generate\(|\.chat\(|\.complete\(', content))
                has_budget = bool(re.search(r'budget|cost_limit|max_tokens', content))

                if has_llm_calls and not has_budget:
                    findings.append(Finding(
                        type="AGENT01_NO_COST_LIMIT",
                        severity=Severity.MEDIUM,
                        message="Agent makes LLM calls without budget/cost limits",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add budget tracking and cost limits",
                    ))
            except Exception:
                pass

        return findings

    def _check_agent02_tool_access_control(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-02: Insufficient Tool Access Control

        Risk: Agent has access to dangerous tools without proper authorization.
        """
        findings = []

        # Dangerous tools that should require authorization
        dangerous_tools = {
            'delete': 'file deletion',
            'drop': 'database drop',
            'exec': 'code execution',
            'system': 'system command',
            'rm ': 'file removal',
            'format': 'disk format',
            'curl': 'external network access',
            'wget': 'download from internet',
        }

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for tool, desc in dangerous_tools.items():
                    if tool in content.lower():
                        # Check if there's authorization logic nearby
                        has_auth = bool(re.search(
                            r'(authorize|permission|confirm|allow|check_access)',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_auth:
                            findings.append(Finding(
                                type="AGENT02_NO_TOOL_AUTH",
                                severity=Severity.HIGH,
                                message=f"Dangerous tool '{tool}' ({desc}) without authorization",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Add authorization checks before destructive operations",
                            ))
                        break  # One finding per file
            except Exception:
                pass

        return findings

    def _check_agent03_planning_injection(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-03: Planning/Reasoning Injection

        Risk: User input influences agent's planning/reasoning in dangerous ways.
        """
        findings = []

        # Patterns where user input goes into planning prompts
        patterns = [
            (r'plan.*=.*f["\'].*\{.*user.*\}', 'User input in planning prompt'),
            (r'system.*=.*\+.*user', 'User input concatenated to system prompt'),
            (r'instructions.*=.*input\(\)', 'User controls instructions'),
            (r'goal.*=.*request\.', 'User controls agent goal'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="AGENT03_PLANNING_INJECTION",
                            severity=Severity.CRITICAL,
                            message=f"Planning injection: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Sanitize user input before using in planning prompts",
                        ))
            except Exception:
                pass

        return findings

    def _check_agent04_tool_hallucination(
        self, skill_path: Path, trace_data: Optional[Dict]
    ) -> List[Finding]:
        """
        AGENT-04: Tool Hallucination

        Risk: Agent invents tools/parameters that don't exist.
        """
        findings = []

        # Static check: Dynamic tool invocation (risky)
        patterns = [
            (r'getattr\(.*tools.*,', 'Dynamic tool lookup'),
            (r'eval\(.*tool', 'Eval-based tool invocation'),
            (r'exec\(.*action', 'Exec-based action execution'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="AGENT04_TOOL_HALLUCINATION",
                            severity=Severity.HIGH,
                            message=f"Tool hallucination risk: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Use explicit tool registry with validation",
                        ))
            except Exception:
                pass

        return findings

    def _check_agent05_state_poisoning(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-05: State Poisoning

        Risk: Agent's memory/state can be corrupted by malicious input.
        """
        findings = []

        # Patterns of state management without validation
        patterns = [
            (r'memory\.append\(user', 'User input directly to memory'),
            (r'state\[.*\]\s*=\s*request', 'Request data to state without validation'),
            (r'history\s*\+=\s*\[.*input.*\]', 'Input appended to history'),
            (r'context\.update\(.*input', 'User input updates context'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="AGENT05_STATE_POISONING",
                            severity=Severity.HIGH,
                            message=f"State poisoning: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Validate and sanitize before updating agent state",
                        ))
            except Exception:
                pass

        return findings

    def _check_agent06_recursive_loops(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-06: Recursive/Infinite Agent Loops

        Risk: Agent calls itself or enters feedback loops.
        """
        findings = []

        # Patterns of recursion without depth limits
        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Check for recursive calls
                if 'def ' in content:
                    import re
                    func_defs = re.findall(r'def\s+(\w+)\s*\(', content)

                    for func_name in func_defs:
                        # Check if function calls itself
                        pattern = rf'def\s+{func_name}\s*\(.*?\):(.*?)(?=\ndef\s|\nclass\s|\Z)'
                        matches = re.finditer(pattern, content, re.DOTALL)

                        for match in matches:
                            func_body = match.group(1)
                            if func_name in func_body:
                                # Has recursion - check for depth limit
                                has_limit = bool(re.search(
                                    r'(depth|level|max_recursion|recursion_limit)',
                                    func_body
                                ))

                                if not has_limit:
                                    line = content[:match.start()].count('\n') + 1
                                    findings.append(Finding(
                                        type="AGENT06_UNBOUNDED_RECURSION",
                                        severity=Severity.HIGH,
                                        message=f"Recursive function '{func_name}' without depth limit",
                                        file=str(file_path.relative_to(skill_path)),
                                        line=line,
                                        remediation="Add max_depth parameter to prevent infinite recursion",
                                    ))
            except Exception:
                pass

        return findings

    def _check_agent07_credential_leakage(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-07: Credential/Secret Leakage in Agent Memory

        Risk: Secrets stored in agent memory leak to users/logs.
        """
        findings = []

        # Patterns where secrets might leak
        patterns = [
            (r'memory\.append\(.*api_key', 'API key in memory'),
            (r'history.*password', 'Password in history'),
            (r'log.*token', 'Token in logs'),
            (r'print.*secret', 'Secret in print statement'),
            (r'response.*credential', 'Credential in response'),
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()
                for pattern, desc in patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        line = content[:match.start()].count('\n') + 1
                        findings.append(Finding(
                            type="AGENT07_CREDENTIAL_LEAK",
                            severity=Severity.CRITICAL,
                            message=f"Credential leakage: {desc}",
                            file=str(file_path.relative_to(skill_path)),
                            line=line,
                            remediation="Never store secrets in memory/history/logs",
                        ))
            except Exception:
                pass

        return findings

    def _check_agent08_context_overflow(
        self, skill_path: Path, trace_data: Optional[Dict]
    ) -> List[Finding]:
        """
        AGENT-08: Context Window Overflow

        Risk: Agent's context grows unbounded causing errors/truncation.
        """
        findings = []

        # Static check: No context management
        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Has message history
                has_history = bool(re.search(r'(history|messages|conversation)', content))

                # Has summarization/truncation
                has_management = bool(re.search(
                    r'(summarize|truncate|compress|max_tokens|context_limit)',
                    content
                ))

                if has_history and not has_management:
                    findings.append(Finding(
                        type="AGENT08_NO_CONTEXT_MGMT",
                        severity=Severity.MEDIUM,
                        message="Agent tracks history without context management",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add summarization or truncation for long conversations",
                    ))
            except Exception:
                pass

        return findings

    def _check_agent09_action_confirmation(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-09: Missing Action Confirmation

        Risk: Agent performs destructive actions without user approval.
        """
        findings = []

        # Destructive actions that should require confirmation
        destructive_actions = [
            'delete',
            'drop',
            'remove',
            'destroy',
            'format',
            'reset',
            'clear',
            'purge',
        ]

        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                for action in destructive_actions:
                    pattern = rf'\b{action}\b.*\('
                    if re.search(pattern, content, re.IGNORECASE):
                        # Check for confirmation logic
                        has_confirm = bool(re.search(
                            r'(confirm|approve|ask_user|permission|verify)',
                            content,
                            re.IGNORECASE
                        ))

                        if not has_confirm:
                            findings.append(Finding(
                                type="AGENT09_NO_CONFIRMATION",
                                severity=Severity.HIGH,
                                message=f"Destructive action '{action}' without confirmation",
                                file=str(file_path.relative_to(skill_path)),
                                line=None,
                                remediation="Add user confirmation before destructive actions",
                            ))
                        break  # One per file
            except Exception:
                pass

        return findings

    def _check_agent10_audit_logging(self, skill_path: Path) -> List[Finding]:
        """
        AGENT-10: Insufficient Audit Logging

        Risk: Agent actions not logged for security monitoring.
        """
        findings = []

        # Check if agent has tool calls but no logging
        for file_path in skill_path.rglob("*.py"):
            try:
                content = file_path.read_text()

                # Has tool/action execution
                has_tools = bool(re.search(
                    r'(execute|invoke|call_tool|run_action)',
                    content
                ))

                # Has logging
                has_logging = bool(re.search(
                    r'(logger\.|logging\.|log\(|audit)',
                    content
                ))

                if has_tools and not has_logging:
                    findings.append(Finding(
                        type="AGENT10_NO_AUDIT_LOG",
                        severity=Severity.MEDIUM,
                        message="Agent executes actions without audit logging",
                        file=str(file_path.relative_to(skill_path)),
                        line=None,
                        remediation="Add audit logging for all agent actions",
                    ))
            except Exception:
                pass

        return findings


def check_owasp_agentic(skill_path: Path, trace_data: Optional[Dict] = None) -> List[Finding]:
    """
    Main entry point for OWASP Agentic checks.

    Args:
        skill_path: Path to skill directory
        trace_data: Optional execution trace data

    Returns:
        List of findings
    """
    checker = OWASPAgenticChecker()
    return checker.check_all(skill_path, trace_data)
