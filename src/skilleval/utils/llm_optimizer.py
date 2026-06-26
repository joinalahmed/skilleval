"""
LLM usage optimization analysis - detect inefficient LLM patterns.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

from skilleval.models import Finding, Severity


class LLMOptimizationAnalyzer(ast.NodeVisitor):
    """Analyze LLM usage for optimization opportunities."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

        # Track LLM calls
        self.llm_calls = []
        self.prompt_variables = {}

        # LLM API patterns
        self.llm_functions = {
            'chat', 'complete', 'generate', 'invoke',
            'create_completion', 'create_chat_completion',
        }

    def analyze(self, code: str) -> List[Finding]:
        """Analyze code for LLM optimization opportunities."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            self._analyze_patterns()
        except SyntaxError:
            pass

        return self.findings

    def visit_Call(self, node: ast.Call):
        """Track LLM API calls."""
        func_name = self._get_func_name(node)

        if any(llm_func in func_name.lower() for llm_func in self.llm_functions):
            self.llm_calls.append({
                'name': func_name,
                'line': node.lineno,
                'args': node.args,
                'keywords': {kw.arg: kw.value for kw in node.keywords},
            })

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Track prompt variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id.lower()
                if 'prompt' in var_name or 'message' in var_name:
                    self.prompt_variables[target.id] = {
                        'value': node.value,
                        'line': node.lineno,
                    }

        self.generic_visit(node)

    def _analyze_patterns(self):
        """Analyze collected patterns for optimization opportunities."""
        # Check for redundant LLM calls in loops
        self._check_llm_in_loops()

        # Check for prompt optimization
        self._check_prompt_efficiency()

        # Check for missing caching
        self._check_missing_cache()

        # Check for token waste
        self._check_token_waste()

        # Check for batch opportunities
        self._check_batch_opportunities()

    def _check_llm_in_loops(self):
        """Detect LLM calls inside loops."""
        # This requires control flow analysis
        # For now, heuristic: multiple calls with same pattern
        if len(self.llm_calls) > 5:
            call_patterns = [call['name'] for call in self.llm_calls]
            if len(set(call_patterns)) < len(call_patterns) / 2:
                self.findings.append(Finding(
                    type="LLM_CALL_IN_LOOP",
                    severity=Severity.MEDIUM,
                    message="Repeated LLM calls detected - consider batching",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=self.llm_calls[0]['line'],
                    remediation="Batch multiple requests into single call or use async/parallel processing.",
                ))

    def _check_prompt_efficiency(self):
        """Check for inefficient prompts."""
        for var_name, info in self.prompt_variables.items():
            value_node = info['value']

            # Check for very long static prompts
            if isinstance(value_node, ast.Constant):
                if isinstance(value_node.value, str):
                    prompt_text = value_node.value

                    # Check length
                    if len(prompt_text) > 2000:
                        self.findings.append(Finding(
                            type="LONG_PROMPT",
                            severity=Severity.LOW,
                            message=f"Very long prompt ({len(prompt_text)} chars) - token cost concern",
                            file=str(self.file_path.relative_to(self.skill_path)),
                            line=info['line'],
                            remediation="Consider prompt compression or splitting context.",
                        ))

                    # Check for repetitive text
                    words = prompt_text.split()
                    if len(words) > 100:
                        unique_ratio = len(set(words)) / len(words)
                        if unique_ratio < 0.5:
                            self.findings.append(Finding(
                                type="REPETITIVE_PROMPT",
                                severity=Severity.LOW,
                                message="Prompt contains repetitive text - wasted tokens",
                                file=str(self.file_path.relative_to(self.skill_path)),
                                line=info['line'],
                                remediation="Remove repetition. Use concise language.",
                            ))

    def _check_missing_cache(self):
        """Check if prompt caching could be used."""
        # Look for static prompt prefixes
        for call in self.llm_calls:
            if 'messages' in call['keywords']:
                # Check if system message is static
                # This is a simplification - real check would analyze message structure
                self.findings.append(Finding(
                    type="CACHE_OPPORTUNITY",
                    severity=Severity.LOW,
                    message="Consider using prompt caching for static system messages",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=call['line'],
                    remediation="Use Claude's prompt caching for system messages and context.",
                ))

    def _check_token_waste(self):
        """Check for token waste patterns."""
        # Check for unnecessary verbosity in prompts
        for var_name, info in self.prompt_variables.items():
            if isinstance(info['value'], ast.Constant):
                if isinstance(info['value'].value, str):
                    text = info['value'].value

                    # Check for verbose phrases
                    verbose_patterns = [
                        r'\bplease\b',
                        r'\bkindly\b',
                        r'\bI would like you to\b',
                        r'\bCould you please\b',
                    ]

                    for pattern in verbose_patterns:
                        if re.search(pattern, text, re.IGNORECASE):
                            self.findings.append(Finding(
                                type="VERBOSE_PROMPT",
                                severity=Severity.LOW,
                                message="Prompt contains verbose language - token waste",
                                file=str(self.file_path.relative_to(self.skill_path)),
                                line=info['line'],
                                remediation="Use concise imperative language. LLM doesn't need politeness.",
                            ))
                            break

    def _check_batch_opportunities(self):
        """Check for opportunities to batch requests."""
        if len(self.llm_calls) > 3:
            # Check if calls are similar (could be batched)
            lines = [call['line'] for call in self.llm_calls]
            if max(lines) - min(lines) < 50:  # Calls are close together
                self.findings.append(Finding(
                    type="BATCH_OPPORTUNITY",
                    severity=Severity.MEDIUM,
                    message=f"{len(self.llm_calls)} LLM calls in close proximity - consider batching",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=min(lines),
                    remediation="Batch similar requests or use async/parallel execution.",
                ))

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return ''


def estimate_token_usage(text: str) -> int:
    """
    Estimate token count for text.

    Uses rough approximation: 1 token ~= 4 characters for English.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    # Very rough estimate
    # Real implementation would use tiktoken
    return len(text) // 4


def estimate_cost(tokens: int, model: str = "claude-sonnet-4") -> float:
    """
    Estimate API cost for token usage.

    Args:
        tokens: Token count
        model: Model name

    Returns:
        Estimated cost in USD
    """
    # Pricing (per million tokens)
    pricing = {
        'claude-opus-4': {'input': 15.0, 'output': 75.0},
        'claude-sonnet-4': {'input': 3.0, 'output': 15.0},
        'claude-haiku-4': {'input': 0.25, 'output': 1.25},
    }

    # Use sonnet pricing as default
    prices = pricing.get(model, pricing['claude-sonnet-4'])

    # Assume 50/50 input/output split
    cost_per_million = (prices['input'] + prices['output']) / 2
    return (tokens / 1_000_000) * cost_per_million


def analyze_llm_usage(file_path: Path, skill_path: Path) -> Tuple[List[Finding], Dict[str, Any]]:
    """
    Analyze LLM usage in Python file.

    Args:
        file_path: Path to Python file
        skill_path: Path to skill root

    Returns:
        Tuple of (findings, usage_stats)
    """
    try:
        code = file_path.read_text()
        analyzer = LLMOptimizationAnalyzer(file_path, skill_path)
        findings = analyzer.analyze(code)

        # Calculate stats
        total_prompt_tokens = 0
        for var_name, info in analyzer.prompt_variables.items():
            if isinstance(info['value'], ast.Constant):
                if isinstance(info['value'].value, str):
                    total_prompt_tokens += estimate_token_usage(info['value'].value)

        stats = {
            'llm_call_count': len(analyzer.llm_calls),
            'estimated_prompt_tokens': total_prompt_tokens,
            'estimated_cost_per_run': estimate_cost(total_prompt_tokens),
        }

        return findings, stats

    except Exception:
        return [], {}
