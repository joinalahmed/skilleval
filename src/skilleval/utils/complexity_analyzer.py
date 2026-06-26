"""
Code complexity and maintainability metrics.
"""

import ast
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ComplexityMetrics:
    """Code complexity metrics."""
    cyclomatic_complexity: int
    cognitive_complexity: int
    lines_of_code: int
    comment_lines: int
    blank_lines: int
    maintainability_index: float
    halstead_metrics: Dict[str, float]
    nesting_depth: int
    function_count: int
    class_count: int


class ComplexityAnalyzer(ast.NodeVisitor):
    """Analyze code complexity metrics."""

    def __init__(self):
        self.cyclomatic = 1
        self.cognitive = 0
        self.nesting_level = 0
        self.max_nesting = 0
        self.function_count = 0
        self.class_count = 0

        # Halstead metrics
        self.operators = []
        self.operands = []

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        self.function_count += 1
        old_nesting = self.nesting_level
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)

        self.generic_visit(node)
        self.nesting_level = old_nesting

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        self.class_count += 1
        self.generic_visit(node)

    def visit_If(self, node: ast.If):
        """Visit if statement."""
        self.cyclomatic += 1
        self.cognitive += 1 + self.nesting_level

        old_nesting = self.nesting_level
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)

        self.generic_visit(node)
        self.nesting_level = old_nesting

    def visit_While(self, node: ast.While):
        """Visit while loop."""
        self.cyclomatic += 1
        self.cognitive += 1 + self.nesting_level

        old_nesting = self.nesting_level
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)

        self.generic_visit(node)
        self.nesting_level = old_nesting

    def visit_For(self, node: ast.For):
        """Visit for loop."""
        self.cyclomatic += 1
        self.cognitive += 1 + self.nesting_level

        old_nesting = self.nesting_level
        self.nesting_level += 1
        self.max_nesting = max(self.max_nesting, self.nesting_level)

        self.generic_visit(node)
        self.nesting_level = old_nesting

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        """Visit exception handler."""
        self.cyclomatic += 1
        self.cognitive += 1

        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp):
        """Visit boolean operation."""
        self.cyclomatic += len(node.values) - 1
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp):
        """Track operators for Halstead."""
        self.operators.append(type(node.op).__name__)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        """Track operands for Halstead."""
        self.operands.append(node.id)
        self.generic_visit(node)


def calculate_complexity(file_path: Path) -> ComplexityMetrics:
    """
    Calculate complexity metrics for a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        ComplexityMetrics object
    """
    try:
        code = file_path.read_text()
        lines = code.splitlines()

        # Count line types
        loc = len([l for l in lines if l.strip()])
        comment_lines = len([l for l in lines if l.strip().startswith('#')])
        blank_lines = len(lines) - loc

        # Parse AST
        tree = ast.parse(code)
        analyzer = ComplexityAnalyzer()
        analyzer.visit(tree)

        # Calculate Halstead metrics
        halstead = _calculate_halstead(analyzer.operators, analyzer.operands)

        # Calculate maintainability index
        # MI = 171 - 5.2*ln(V) - 0.23*G - 16.2*ln(LOC)
        # Where V = Halstead volume, G = cyclomatic complexity
        import math
        volume = halstead.get('volume', 0)
        if volume > 0 and loc > 0:
            mi = max(0, min(100, (
                171
                - 5.2 * math.log(volume)
                - 0.23 * analyzer.cyclomatic
                - 16.2 * math.log(loc)
            ) * 100 / 171))
        else:
            mi = 100.0

        return ComplexityMetrics(
            cyclomatic_complexity=analyzer.cyclomatic,
            cognitive_complexity=analyzer.cognitive,
            lines_of_code=loc,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            maintainability_index=mi,
            halstead_metrics=halstead,
            nesting_depth=analyzer.max_nesting,
            function_count=analyzer.function_count,
            class_count=analyzer.class_count,
        )

    except Exception:
        # Return default metrics on error
        return ComplexityMetrics(
            cyclomatic_complexity=0,
            cognitive_complexity=0,
            lines_of_code=0,
            comment_lines=0,
            blank_lines=0,
            maintainability_index=100.0,
            halstead_metrics={},
            nesting_depth=0,
            function_count=0,
            class_count=0,
        )


def _calculate_halstead(operators: List[str], operands: List[str]) -> Dict[str, float]:
    """Calculate Halstead complexity metrics."""
    n1 = len(set(operators))  # Unique operators
    n2 = len(set(operands))   # Unique operands
    N1 = len(operators)       # Total operators
    N2 = len(operands)        # Total operands

    if n1 == 0 and n2 == 0:
        return {}

    import math

    n = n1 + n2  # Program vocabulary
    N = N1 + N2  # Program length

    if n > 0:
        volume = N * math.log2(n) if n > 1 else N
        difficulty = (n1 / 2) * (N2 / n2) if n2 > 0 else 0
        effort = difficulty * volume
        time = effort / 18  # Seconds
        bugs = volume / 3000  # Estimated bugs

        return {
            'vocabulary': n,
            'length': N,
            'volume': volume,
            'difficulty': difficulty,
            'effort': effort,
            'time_seconds': time,
            'estimated_bugs': bugs,
        }

    return {}


def assess_maintainability(metrics: ComplexityMetrics) -> Tuple[str, List[str]]:
    """
    Assess code maintainability.

    Args:
        metrics: Complexity metrics

    Returns:
        Tuple of (grade, recommendations)
    """
    issues = []

    # Check cyclomatic complexity
    if metrics.cyclomatic_complexity > 20:
        issues.append("Very high cyclomatic complexity - refactor into smaller functions")
    elif metrics.cyclomatic_complexity > 10:
        issues.append("High cyclomatic complexity - consider refactoring")

    # Check cognitive complexity
    if metrics.cognitive_complexity > 15:
        issues.append("High cognitive complexity - difficult to understand")

    # Check nesting depth
    if metrics.nesting_depth > 4:
        issues.append(f"Deep nesting ({metrics.nesting_depth} levels) - flatten logic")

    # Check maintainability index
    if metrics.maintainability_index < 20:
        grade = "F"
        issues.append("Very low maintainability - major refactoring needed")
    elif metrics.maintainability_index < 40:
        grade = "D"
        issues.append("Low maintainability - refactoring recommended")
    elif metrics.maintainability_index < 60:
        grade = "C"
    elif metrics.maintainability_index < 80:
        grade = "B"
    else:
        grade = "A"

    # Check function count
    if metrics.lines_of_code > 0:
        avg_func_size = metrics.lines_of_code / max(1, metrics.function_count)
        if avg_func_size > 50:
            issues.append("Average function size too large - break down functions")

    return grade, issues
