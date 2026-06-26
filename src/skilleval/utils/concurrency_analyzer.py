"""
Concurrency and thread safety analysis - deterministic checks.
"""

import ast
from pathlib import Path
from typing import List, Set

from skilleval.models import Finding, Severity


class ConcurrencyAnalyzer(ast.NodeVisitor):
    """Detect concurrency issues and race conditions."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

        # Track concurrency patterns
        self.uses_threading = False
        self.uses_asyncio = False
        self.uses_multiprocessing = False
        self.shared_state = set()
        self.locks_used = set()

    def analyze(self, code: str) -> List[Finding]:
        """Analyze concurrency issues."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            self._check_concurrency_safety()
        except SyntaxError:
            pass
        return self.findings

    def visit_Import(self, node: ast.Import):
        """Track concurrency-related imports."""
        for alias in node.names:
            if alias.name == 'threading':
                self.uses_threading = True
            elif alias.name == 'asyncio':
                self.uses_asyncio = True
            elif alias.name == 'multiprocessing':
                self.uses_multiprocessing = True

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check async function patterns."""
        # Async function without await
        if node.returns and isinstance(node.returns, ast.Name):
            if node.returns.id == 'Coroutine':
                has_await = any(
                    isinstance(n, ast.Await) for n in ast.walk(node)
                )
                if not has_await:
                    self.findings.append(Finding(
                        type="ASYNC_WITHOUT_AWAIT",
                        severity=Severity.MEDIUM,
                        message=f"Async function '{node.name}' doesn't use await",
                        file=str(self.file_path.relative_to(self.skill_path)),
                        line=node.lineno,
                        remediation="Use await or make function synchronous",
                    ))

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Check async function patterns."""
        # Async function without await
        has_await = any(isinstance(n, ast.Await) for n in ast.walk(node))
        if not has_await:
            self.findings.append(Finding(
                type="ASYNC_WITHOUT_AWAIT",
                severity=Severity.MEDIUM,
                message=f"Async function '{node.name}' doesn't use await",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Use await or make function synchronous",
            ))

        self.generic_visit(node)

    def visit_Global(self, node: ast.Global):
        """Track global variables (potential shared state)."""
        for name in node.names:
            self.shared_state.add(name)

        if self.uses_threading or self.uses_multiprocessing:
            self.findings.append(Finding(
                type="GLOBAL_WITH_CONCURRENCY",
                severity=Severity.HIGH,
                message="Global variable used with threading - race condition risk",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Use locks or thread-local storage",
            ))

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        """Track threading/async operations."""
        func_name = self._get_func_name(node)

        # Thread creation
        if func_name in {'Thread', 'Process'}:
            self.findings.append(Finding(
                type="THREAD_CREATED",
                severity=Severity.LOW,
                message="Thread/Process created - ensure proper synchronization",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Use locks for shared state, join threads properly",
            ))

        # Sleep in async code (blocks event loop)
        if func_name == 'sleep' and self.uses_asyncio:
            # Check if it's time.sleep vs asyncio.sleep
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'time':
                        self.findings.append(Finding(
                            type="BLOCKING_SLEEP_IN_ASYNC",
                            severity=Severity.HIGH,
                            message="time.sleep() blocks event loop - use asyncio.sleep()",
                            file=str(self.file_path.relative_to(self.skill_path)),
                            line=node.lineno,
                            remediation="Replace time.sleep() with await asyncio.sleep()",
                        ))

        # Missing await on coroutine
        if func_name in {'sleep', 'gather', 'wait', 'wait_for'}:
            # Check if in await context
            # Simplified check - real implementation would track context
            pass

        self.generic_visit(node)

    def _check_concurrency_safety(self):
        """Check overall concurrency safety."""
        # Shared state without locks
        if self.shared_state and (self.uses_threading or self.uses_multiprocessing):
            if not self.locks_used:
                self.findings.append(Finding(
                    type="SHARED_STATE_NO_LOCKS",
                    severity=Severity.CRITICAL,
                    message="Shared state with threading but no locks detected",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=None,
                    remediation="Use threading.Lock() to protect shared state",
                ))

    def _get_func_name(self, node: ast.Call) -> str:
        """Extract function name."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return ''


class TypeSafetyAnalyzer(ast.NodeVisitor):
    """Analyze type safety and type hints."""

    def __init__(self, file_path: Path, skill_path: Path):
        self.file_path = file_path
        self.skill_path = skill_path
        self.findings: List[Finding] = []

        self.functions_total = 0
        self.functions_typed = 0

    def analyze(self, code: str) -> List[Finding]:
        """Analyze type safety."""
        try:
            tree = ast.parse(code)
            self.visit(tree)
            self._assess_type_coverage()
        except SyntaxError:
            pass
        return self.findings

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function type hints."""
        # Skip private functions and test functions
        if node.name.startswith('_') or node.name.startswith('test_'):
            self.generic_visit(node)
            return

        self.functions_total += 1

        # Check return type annotation
        has_return_type = node.returns is not None

        # Check parameter type annotations
        params_with_types = sum(
            1 for arg in node.args.args
            if arg.annotation is not None
        )
        total_params = len(node.args.args)

        # Function is considered typed if it has return type and all params typed
        if has_return_type and (total_params == 0 or params_with_types == total_params):
            self.functions_typed += 1
        else:
            self.findings.append(Finding(
                type="MISSING_TYPE_HINTS",
                severity=Severity.LOW,
                message=f"Function '{node.name}' missing type hints",
                file=str(self.file_path.relative_to(self.skill_path)),
                line=node.lineno,
                remediation="Add type hints for parameters and return value",
            ))

        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Track annotated assignments (good practice)."""
        self.generic_visit(node)

    def _assess_type_coverage(self):
        """Assess overall type hint coverage."""
        if self.functions_total > 0:
            coverage = (self.functions_typed / self.functions_total) * 100

            if coverage < 30:
                self.findings.append(Finding(
                    type="LOW_TYPE_COVERAGE",
                    severity=Severity.MEDIUM,
                    message=f"Low type hint coverage: {coverage:.0f}%",
                    file=str(self.file_path.relative_to(self.skill_path)),
                    line=None,
                    remediation="Add type hints to improve code safety and IDE support",
                ))


def analyze_concurrency(file_path: Path, skill_path: Path) -> List[Finding]:
    """Analyze concurrency issues."""
    try:
        code = file_path.read_text()
        analyzer = ConcurrencyAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception:
        return []


def analyze_type_safety(file_path: Path, skill_path: Path) -> List[Finding]:
    """Analyze type safety."""
    try:
        code = file_path.read_text()
        analyzer = TypeSafetyAnalyzer(file_path, skill_path)
        return analyzer.analyze(code)
    except Exception:
        return []
