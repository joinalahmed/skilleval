"""
Resource leak and management analysis - deterministic checks.
"""

import ast
from pathlib import Path
from typing import List, Set, Dict

from skilleval.models import Finding, Severity


class ResourceLeakAnalyzer(ast.NodeVisitor):
    """Detect resource leaks and management issues."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

        # Track resources
        self.opened_files = {}  # var_name -> line_number
        self.closed_files = set()
        self.connections = {}  # var_name -> line_number
        self.locks = {}  # var_name -> line_number

        # Track context managers
        self.in_with_statement = False

    def analyze(self, code: str) -> List[Finding]:
        """Analyze code for resource leaks."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            self._check_unclosed_resources()
        except SyntaxError:
            pass
        return self.findings

    def visit_With(self, node: ast.With):
        """Track context managers (good practice)."""
        old_with = self.in_with_statement
        self.in_with_statement = True
        self.generic_visit(node)
        self.in_with_statement = old_with

    def visit_Call(self, node: ast.Call):
        """Track resource allocations and releases."""
        func_name = self._get_func_name(node)

        # File operations
        if func_name == 'open':
            if not self.in_with_statement:
                self.findings.append(Finding(
                    type="FILE_NOT_IN_CONTEXT_MANAGER",
                    severity=Severity.MEDIUM,
                    message="File opened without context manager (with statement)",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Use 'with open(...) as f:' to ensure file is closed",
                ))

        # Database connections
        elif func_name in {'connect', 'create_engine', 'Connection'}:
            if not self.in_with_statement:
                self.findings.append(Finding(
                    type="CONNECTION_NOT_IN_CONTEXT_MANAGER",
                    severity=Severity.HIGH,
                    message="Database connection without context manager",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Use context manager or ensure .close() is called",
                ))

        # Threading locks
        elif func_name in {'Lock', 'RLock', 'Semaphore'}:
            self.findings.append(Finding(
                type="LOCK_USAGE",
                severity=Severity.MEDIUM,
                message="Threading lock - ensure it's released in finally block",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Use 'with lock:' or ensure release in finally block",
            ))

        # Temporary files
        elif func_name == 'NamedTemporaryFile':
            if not any(kw.arg == 'delete' for kw in node.keywords):
                self.findings.append(Finding(
                    type="TEMP_FILE_NOT_DELETED",
                    severity=Severity.LOW,
                    message="NamedTemporaryFile without explicit delete parameter",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Specify delete=True or use context manager",
                ))

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check for missing cleanup in functions."""
        # Check if function has try/finally for cleanup
        has_finally = any(
            isinstance(n, ast.Try) and n.finalbody
            for n in ast.walk(node)
        )

        # Check if function uses resources
        has_open = any(
            isinstance(n, ast.Call) and
            self._get_func_name(n) in {'open', 'connect'}
            for n in ast.walk(node)
        )

        if has_open and not has_finally and not self.in_with_statement:
            # Check if it uses context managers
            has_with = any(isinstance(n, ast.With) for n in node.body)
            if not has_with:
                self.findings.append(Finding(
                    type="MISSING_RESOURCE_CLEANUP",
                    severity=Severity.MEDIUM,
                    message=f"Function '{node.name}' opens resources without cleanup",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=node.lineno,
                    remediation="Use context managers or try/finally blocks",
                ))

        self.generic_visit(node)

    def _check_unclosed_resources(self):
        """Check for resources that were opened but never closed."""
        # This is a simplified check - full analysis would need data flow
        pass

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name from call."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ''


class ErrorHandlingAnalyzer(ast.NodeVisitor):
    """Analyze error handling patterns."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

    def analyze(self, code: str) -> List[Finding]:
        """Analyze error handling."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError:
            pass
        return self.findings

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Check exception handling patterns."""
        # Bare except
        if node.type is None:
            self.findings.append(Finding(
                type="BARE_EXCEPT",
                severity=Severity.HIGH,
                message="Bare except clause catches all exceptions including SystemExit",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Catch specific exceptions or use 'except Exception:'",
            ))

        # Exception pass (swallowing errors)
        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            self.findings.append(Finding(
                type="EXCEPTION_SWALLOWED",
                severity=Severity.HIGH,
                message="Exception caught and silently ignored",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Log the exception or re-raise if you can't handle it",
            ))

        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise):
        """Check raise statements."""
        # Raising generic Exception
        if isinstance(node.exc, ast.Call):
            if isinstance(node.exc.func, ast.Name):
                if node.exc.func.id == 'Exception':
                    self.findings.append(Finding(
                        type="GENERIC_EXCEPTION",
                        severity=Severity.LOW,
                        message="Raising generic Exception - use specific exception type",
                        file=str(self.file_path.relative_to(self.skill_path)),
                        line=node.lineno,
                        remediation="Define or use specific exception classes",
                    ))

        self.generic_visit(node)


class PerformanceAnalyzer(ast.NodeVisitor):
    """Detect performance anti-patterns."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []
        self.in_loop = False

    def analyze(self, code: str) -> List[Finding]:
        """Analyze performance issues."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
        except SyntaxError:
            pass
        return self.findings

    def visit_For(self, node: ast.For):
        """Track loops for performance checks."""
        old_loop = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = old_loop

    def visit_While(self, node: ast.While):
        """Track while loops."""
        old_loop = self.in_loop
        self.in_loop = True
        self.generic_visit(node)
        self.in_loop = old_loop

    def visit_Call(self, node: ast.Call):
        """Check for expensive operations in loops."""
        func_name = self._get_func_name(node)

        # String concatenation in loop
        if self.in_loop:
            # Check for += with strings
            # This is simplified - real check would track variable types
            self.findings.append(Finding(
                type="FUNCTION_CALL_IN_LOOP",
                severity=Severity.LOW,
                message=f"Function call '{func_name}' in loop - consider optimization",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Move invariant operations outside loop or use list comprehension",
            ))

        # List append in loop (should use list comprehension)
        if self.in_loop and func_name == 'append':
            pass  # Could suggest list comprehension

        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp):
        """Check list comprehensions."""
        # Nested list comprehensions (hard to read)
        nested_comps = sum(1 for _ in ast.walk(node) if isinstance(_, ast.ListComp))
        if nested_comps > 2:
            self.findings.append(Finding(
                type="NESTED_COMPREHENSION",
                severity=Severity.MEDIUM,
                message="Deeply nested list comprehension - hard to read",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Break into multiple statements for clarity",
            ))

        self.generic_visit(node)

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ''


def analyze_resource_management(file_path: Path, skill_path: Path) -> List[Finding]:
    """Analyze resource management."""
    try:
        code = file_path.read_text()
        analyzer = ResourceLeakAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception:
        return []


def analyze_error_handling(file_path: Path, skill_path: Path) -> List[Finding]:
    """Analyze error handling."""
    try:
        code = file_path.read_text()
        analyzer = ErrorHandlingAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception:
        return []


def analyze_performance(file_path: Path, skill_path: Path) -> List[Finding]:
    """Analyze performance patterns."""
    try:
        code = file_path.read_text()
        analyzer = PerformanceAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception:
        return []
