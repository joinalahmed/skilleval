#!/usr/bin/env python3
"""
Trace Analysis Tool - Comprehensive log analysis.

Usage:
    python3 analyze_traces.py /path/to/report.json
    python3 analyze_traces.py --aggregate /path/to/reports/
"""

import sys
import json
from pathlib import Path
import argparse

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skilleval.utils.trace_analytics import (
    TraceAnalytics,
    TraceAggregator,
    AnomalyDetector,
)


def print_section(title: str):
    """Print section header."""
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def analyze_single_report(report_path: Path):
    """Analyze a single evaluation report."""
    print(f"\nAnalyzing: {report_path}")

    with open(report_path) as f:
        report = json.load(f)

    # Extract trace data from report
    # Note: Current reports don't include full traces
    # This is a demonstration of what would be analyzed

    print_section("Report Summary")
    print(f"Skill: {report['skill_name']}")
    print(f"Final Score: {report['final_score']}/100")
    print(f"Grade: {report['grade']}")
    print(f"Duration: {report['total_duration_seconds']:.1f}s")

    # Harness details
    harness = report.get('pillar_scores', {}).get('harness', {})
    if harness:
        print(f"\nHarness Score: {harness['score']}/100")
        details = harness.get('details', {})

        print_section("Functional Results")
        for result in details.get('functional_results', []):
            print(f"\nCase {result['case_id']}:")
            print(f"  Baseline: {result['baseline_score']:.1f}")
            print(f"  Skill: {result['skill_score']:.1f}")
            print(f"  Improvement: {result['improvement']:+.1f} ({result['improvement_pct']:+.1f}%)")

        print_section("Safety Checks")
        safety_checks = details.get('safety_checks', [])
        if safety_checks:
            for check in safety_checks:
                print(f"\n{check['check']}:")
                print(f"  Score: {check['score']:.1f}")
                print(f"  Severity: {check['severity']}")
                if 'details' in check:
                    for key, value in check['details'].items():
                        print(f"  {key}: {value}")
        else:
            print("No safety checks recorded")

    # Recommendations
    print_section("Analysis & Recommendations")

    if report['final_score'] < 60:
        print("⚠️  Score below acceptable threshold")

    harness_score = harness.get('score', 0)
    if harness_score < 50:
        print("⚠️  Harness performance needs improvement")
        print("   Recommendations:")
        print("   - Review agent behavior for planning loops")
        print("   - Check if skill instructions are clear")
        print("   - Verify eval cases have proper graders")

    print("\n")


def analyze_aggregate(reports_dir: Path):
    """Aggregate analysis across multiple reports."""
    print(f"\nAggregating reports from: {reports_dir}")

    report_files = list(reports_dir.glob("*_report.json"))

    if not report_files:
        print("No report files found!")
        return

    print(f"Found {len(report_files)} reports")

    # Load all reports
    reports = []
    for report_file in report_files:
        try:
            with open(report_file) as f:
                reports.append(json.load(f))
        except:
            print(f"Failed to load: {report_file}")

    print_section("Aggregate Statistics")

    # Overall metrics
    scores = [r['final_score'] for r in reports]
    print(f"\nTotal Evaluations: {len(reports)}")
    print(f"Average Score: {sum(scores) / len(scores):.1f}/100")
    print(f"Highest Score: {max(scores):.1f}")
    print(f"Lowest Score: {min(scores):.1f}")

    # Grade distribution
    from collections import Counter
    grades = Counter([r['grade'] for r in reports])
    print(f"\nGrade Distribution:")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grades.get(grade, 0)
        pct = count / len(reports) * 100
        bar = '█' * int(pct / 2)
        print(f"  {grade}: {count:2d} ({pct:5.1f}%) {bar}")

    # Pillar breakdown
    print_section("Pillar Performance")

    static_scores = [r['pillar_scores']['static_tests']['score'] for r in reports]
    security_scores = [r['pillar_scores']['security']['score'] for r in reports]
    harness_scores = [r['pillar_scores']['harness']['score'] for r in reports]

    print(f"Static Tests:  {sum(static_scores) / len(static_scores):.1f}/100")
    print(f"Security:      {sum(security_scores) / len(security_scores):.1f}/100")
    print(f"Harness:       {sum(harness_scores) / len(harness_scores):.1f}/100")

    # Duration analysis
    durations = [r['total_duration_seconds'] for r in reports]
    print(f"\nExecution Time:")
    print(f"  Average: {sum(durations) / len(durations):.1f}s")
    print(f"  Fastest: {min(durations):.1f}s")
    print(f"  Slowest: {max(durations):.1f}s")

    # Recommendations
    print_section("Recommendations")

    # Skills needing improvement
    failing = [r for r in reports if r['final_score'] < 60]
    if failing:
        print(f"\n⚠️  {len(failing)} skills below acceptable threshold:")
        for r in failing[:5]:
            print(f"   - {r['skill_name']}: {r['final_score']:.1f}/100")

    # Skills with low harness scores
    low_harness = [r for r in reports if r['pillar_scores']['harness']['score'] < 50]
    if low_harness:
        print(f"\n⚠️  {len(low_harness)} skills with low harness scores:")
        for r in low_harness[:5]:
            print(f"   - {r['skill_name']}: {r['pillar_scores']['harness']['score']:.1f}/100")
        print("\n   Suggestions:")
        print("   - Add deterministic graders to eval cases")
        print("   - Review skill instructions for clarity")
        print("   - Check if prompts match expected outputs")

    print("\n")


def demonstrate_analytics():
    """Demonstrate analytics capabilities with sample data."""
    print_section("Trace Analytics Demonstration")

    # Sample trace data
    sample_trace = {
        'provider': 'google',
        'model': 'gemini-3.5-flash',
        'turn_count': 5,
        'total_tokens': 15000,
        'total_input_tokens': 9000,
        'total_output_tokens': 6000,
        'duration_seconds': 12.5,
        'success': True,
        'tool_uses': [
            {'turn': 1, 'tool': 'read_file', 'args': {'path': 'input.txt'}},
            {'turn': 2, 'tool': 'write_file', 'args': {'path': 'output.txt', 'content': 'result'}},
            {'turn': 3, 'tool': 'read_file', 'args': {'path': 'output.txt'}},
        ],
        'messages': [
            {'turn': 1, 'role': 'model', 'text': 'I will read the input file'},
            {'turn': 2, 'role': 'model', 'text': 'Now writing the output'},
            {'turn': 3, 'role': 'model', 'text': 'Verifying the result'},
        ],
    }

    analytics = TraceAnalytics()

    # Performance analysis
    print("\n1. Performance Metrics:")
    perf = analytics.analyze_performance(sample_trace)
    print(f"   Total Duration: {perf.total_duration:.2f}s")
    print(f"   Avg Turn Time: {perf.avg_turn_time:.2f}s")
    print(f"   Tokens/Second: {perf.tokens_per_second:.0f}")
    print(f"   Tokens/Turn: {perf.tokens_per_turn:.0f}")

    # Tool patterns
    print("\n2. Tool Usage Patterns:")
    patterns = analytics.analyze_tool_patterns(sample_trace)
    for pattern in patterns:
        print(f"   {' → '.join(pattern.sequence)}: {pattern.frequency} times")

    # Behavior
    print("\n3. Behavioral Analysis:")
    behavior = analytics.analyze_behavior(sample_trace)
    print(f"   Action Ratio: {behavior.action_ratio:.1%}")
    print(f"   Pattern: {' → '.join(behavior.think_act_pattern)}")
    print(f"   Decision Quality: {behavior.decision_quality:.0f}/100")
    print(f"   Self-Corrections: {behavior.self_correction_count}")

    # Cost analysis
    print("\n4. Cost Analysis:")
    cost = analytics.detailed_cost_analysis(sample_trace)
    print(f"   Total Cost: ${cost['total_cost']:.4f}")
    print(f"   Cost/Turn: ${cost['cost_per_turn']:.4f}")
    print(f"   Cost/Tool: ${cost['cost_per_tool']:.4f}")
    print(f"   Wasted Cost: ${cost['wasted_cost']:.4f}")

    # Quality
    print("\n5. Response Quality:")
    quality = analytics.analyze_response_quality(sample_trace)
    print(f"   Avg Message Length: {quality['avg_length']:.0f} chars")
    print(f"   Coherence Score: {quality['coherence_score']:.0f}/100")
    print(f"   Degradation: {quality['degradation_detected']}")

    print("\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Analyze evaluation traces')
    parser.add_argument('path', nargs='?', help='Path to report.json or reports directory')
    parser.add_argument('--aggregate', action='store_true', help='Aggregate analysis of multiple reports')
    parser.add_argument('--demo', action='store_true', help='Show analytics demonstration')

    args = parser.parse_args()

    if args.demo:
        demonstrate_analytics()
        return

    if not args.path:
        print("Usage: python3 analyze_traces.py <path>")
        print("       python3 analyze_traces.py --aggregate <reports_dir>")
        print("       python3 analyze_traces.py --demo")
        return

    path = Path(args.path)

    if not path.exists():
        print(f"Error: Path not found: {path}")
        return

    if args.aggregate or path.is_dir():
        analyze_aggregate(path)
    else:
        analyze_single_report(path)


if __name__ == "__main__":
    main()
