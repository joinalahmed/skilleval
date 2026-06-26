"""
Advanced AST-based code analysis for deeper security and quality checks.
"""

import ast
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict

from skilleval.models import Finding, Severity


class ASTSecurityAnalyzer(ast.NodeVisitor):
    """AST-based security analyzer for Python code."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

        # Track context
        self.current_function = None
        self.function_calls = []
        self.imports = set()
        self.dangerous_modules = set()

        # Data flow tracking
        self.tainted_variables = set()
        self.user_input_sources = {'input', 'request.form', 'request.args', 'sys.argv'}
        self.dangerous_sinks = {'eval', 'exec', 'os.system', 'subprocess.call'}

        # Track variable assignments
        self.variable_sources = {}  # var_name -> source_type

    def analyze(self, code: str) -> List[Finding]:
        """Analyze Python code using AST."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError as e:
            self.findings.append(Finding(
                type="SYNTAX_ERROR",
                severity=Severity.HIGH,
                message=f"Syntax error in code: {e}",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=e.lineno,
                remediation="Fix syntax errors before deployment",
            ))

        return self.findings

    def visit_Import(self, node: ast.Import):
        """Track imports."""
        for alias in node.names:
            self.imports.add(alias.name)

            # Flag dangerous imports
            if alias.name in {'pickle', 'marshal', 'shelve'}:
                self.dangerous_modules.add(alias.name)
                self.findings.append(Finding(
                    type="DANGEROUS_IMPORT",
                    severity=Severity.MEDIUM,
                    message=f"Potentially dangerous import: {alias.name}",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation=f"Avoid {alias.name} or use safer alternatives. Validate all data.",
                    owasp_id="A08:2021",
                ))

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Track from imports."""
        if node.module:
            self.imports.add(node.module)

            # Check for dangerous subprocess imports
            if node.module == 'subprocess':
                for alias in node.names:
                    if alias.name in {'call', 'Popen', 'run'}:
                        # Check if shell=True is used later
                        pass  # Will be caught in visit_Call

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Analyze function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        # Check for overly complex functions
        complexity = self._calculate_complexity(node)
        if complexity > 10:
            self.findings.append(Finding(
                type="HIGH_COMPLEXITY",
                severity=Severity.MEDIUM,
                message=f"Function '{node.name}' has high cyclomatic complexity: {complexity}",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Refactor into smaller functions. Target complexity < 10.",
            ))

        # Check for missing docstrings
        if not ast.get_docstring(node):
            if not node.name.startswith('_'):  # Ignore private functions
                self.findings.append(Finding(
                    type="MISSING_DOCSTRING",
                    severity=Severity.LOW,
                    message=f"Public function '{node.name}' missing docstring",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Add docstring describing purpose, args, and return value.",
                ))

        # Check for too many parameters
        if len(node.args.args) > 5:
            self.findings.append(Finding(
                type="TOO_MANY_PARAMETERS",
                severity=Severity.LOW,
                message=f"Function '{node.name}' has {len(node.args.args)} parameters (>5)",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Consider using a config object or dataclass for parameters.",
            ))

        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call):
        """Analyze function calls for security issues."""
        # Get function name
        func_name = self._get_call_name(node)

        # Track all calls
        self.function_calls.append((func_name, node.lineno))

        # Check for dangerous eval/exec
        if func_name in {'eval', 'exec'}:
            # Check if argument is tainted
            if node.args:
                arg = node.args[0]
                if self._is_tainted(arg):
                    self.findings.append(Finding(
                        type="TAINTED_EVAL",
                        severity=Severity.CRITICAL,
                        message=f"User input passed to {func_name}() - arbitrary code execution risk",
                        file=str(self.file_path.relative_to(self.skill_path)),
                        line=node.lineno,
                        remediation=f"Never use {func_name}() with user input. Use safer alternatives.",
                        owasp_id="A03:2021",
                    ))

        # Check for shell=True with user input
        if func_name in {'subprocess.call', 'subprocess.run', 'subprocess.Popen'}:
            for keyword in node.keywords:
                if keyword.arg == 'shell' and self._is_true(keyword.value):
                    # Check if command contains user input
                    if node.args and self._is_tainted(node.args[0]):
                        self.findings.append(Finding(
                            type="TAINTED_SHELL_COMMAND",
                            severity=Severity.CRITICAL,
                            message="User input in shell command - command injection risk",
                            file=str(self.file_path.relative_to(self.skill_path)),
                            line=node.lineno,
                            remediation="Use shell=False and pass command as list. Validate all inputs.",
                            owasp_id="A03:2021",
                        ))

        # Check for SQL query construction
        if func_name in {'execute', 'executemany', 'cursor.execute'}:
            if node.args:
                query_arg = node.args[0]
                # Check for string concatenation or formatting
                if isinstance(query_arg, (ast.BinOp, ast.JoinedStr, ast.Call)):
                    if self._contains_string_formatting(query_arg):
                        self.findings.append(Finding(
                            type="SQL_INJECTION_RISK",
                            severity=Severity.HIGH,
                            message="SQL query uses string formatting - injection risk",
                            file=str(self.file_path.relative_to(self.skill_path)),
                            line=node.lineno,
                            remediation="Use parameterized queries with ? or %s placeholders.",
                            owasp_id="A03:2021",
                        ))

        # Check for LLM API calls with secrets
        if func_name in {'chat', 'complete', 'generate', 'invoke'}:
            # Check if any arguments contain sensitive data
            for arg in node.args:
                if self._contains_secret_reference(arg):
                    self.findings.append(Finding(
                        type="LLM06_SECRET_IN_PROMPT",
                        severity=Severity.CRITICAL,
                        message="Secrets/credentials may be sent to LLM",
                        file=str(self.file_path.relative_to(self.skill_path)),
                        line=node.lineno,
                        remediation="Never send secrets to LLM. Redact sensitive data.",
                        owasp_id="LLM06",
                    ))

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        """Track variable assignments for data flow analysis."""
        # Check if RHS is user input
        if isinstance(node.value, ast.Call):
            func_name = self._get_call_name(node.value)
            if func_name in self.user_input_sources:
                # Mark all LHS variables as tainted
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.tainted_variables.add(target.id)
                        self.variable_sources[target.id] = 'user_input'

        # Check for hardcoded secrets in assignments
        if isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                value = node.value.value
                # Check for patterns
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id.lower()
                        if any(keyword in var_name for keyword in ['key', 'token', 'password', 'secret']):
                            if len(value) > 20 and not value.startswith(('http', '//', '.')):
                                self.findings.append(Finding(
                                    type="HARDCODED_SECRET",
                                    severity=Severity.CRITICAL,
                                    message=f"Potential hardcoded secret in variable '{target.id}'",
                                    file=str(self.file_path.relative_to(self.skill_path)),
                                    line=node.lineno,
                                    remediation="Use environment variables or secret management.",
                                ))

        self.generic_visit(node)

    def visit_While(self, node: ast.While):
        """Check for infinite loops."""
        # Check if condition is always True
        if isinstance(node.test, ast.Constant) and node.test.value is True:
            # Check if there's a break statement
            has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
            if not has_break:
                self.findings.append(Finding(
                    type="INFINITE_LOOP",
                    severity=Severity.HIGH,
                    message="Infinite loop without break condition",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Add break condition or max iteration limit.",
                    owasp_id="LLM04",
                ))

        self.generic_visit(node)

    def visit_For(self, node: ast.For):
        """Check for expensive loops."""
        # Check for nested loops (complexity issue)
        nested_loops = sum(1 for n in ast.walk(node) if isinstance(n, (ast.For, ast.While)))
        if nested_loops > 3:
            self.findings.append(Finding(
                type="DEEPLY_NESTED_LOOPS",
                severity=Severity.MEDIUM,
                message=f"Deeply nested loops (depth {nested_loops}) - performance concern",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Consider algorithmic optimization or vectorization.",
            ))

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> str:
        """Extract function name from Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            # Handle module.function
            parts = []
            current = node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return '.'.join(reversed(parts))
        return ''

    def _is_tainted(self, node: ast.AST) -> bool:
        """Check if expression contains tainted variables."""
        if isinstance(node, ast.Name):
            return node.id in self.tainted_variables
        elif isinstance(node, ast.BinOp):
            return self._is_tainted(node.left) or self._is_tainted(node.right)
        elif isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            return func_name in self.user_input_sources
        return False

    def _is_true(self, node: ast.AST) -> bool:
        """Check if node is constant True."""
        return isinstance(node, ast.Constant) and node.value is True

    def _contains_string_formatting(self, node: ast.AST) -> bool:
        """Check if node contains string formatting."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return True
        elif isinstance(node, ast.JoinedStr):  # f-string
            return True
        elif isinstance(node, ast.Call):
            func_name = self._get_call_name(node)
            if func_name == 'format':
                return True
        return False

    def _contains_secret_reference(self, node: ast.AST) -> bool:
        """Check if node references secret variables."""
        if isinstance(node, ast.Name):
            var_name = node.id.lower()
            return any(keyword in var_name for keyword in ['key', 'token', 'password', 'secret'])
        elif isinstance(node, ast.JoinedStr):
            # Check f-string values
            for value in node.values:
                if isinstance(value, ast.FormattedValue):
                    if self._contains_secret_reference(value.value):
                        return True
        return False

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Add 1 for each decision point
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity


def analyze_python_file(file_path: Path, skill_path: Path) -> List[Finding]:
    """
    Analyze a Python file using AST.

    Args:
        file_path: Path to Python file
        skill_path: Path to skill root

    Returns:
        List of findings
    """
    try:
        code = file_path.read_text()
        analyzer = ASTSecurityAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception as e:
        return [Finding(
            type="ANALYSIS_ERROR",
            severity=Severity.LOW,
            message=f"Could not analyze file: {e}",
            file=str(file_path.relative_to(skill_path)),
            line=None,
            remediation="Check file syntax and encoding.",
        )]
