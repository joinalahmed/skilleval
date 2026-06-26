#!/usr/bin/env python3
"""
Analyze batch evaluation results and generate summary report.
"""

import json
import csv
from pathlib import Path
from collections import Counter
from typing import List, Dict


def analyze_results(results_dir: Path):
    """Analyze batch evaluation results."""

    print("="*70)
    print("SkillEval Batch Evaluation Analysis")
    print("="*70)
    print()

    # Read summary CSV
    summary_csv = results_dir / "summary.csv"
    if not summary_csv.exists():
        print(f"ERROR: {summary_csv} not found")
        return

    skills = []
    with open(summary_csv) as f:
        reader = csv.DictReader(f)
        skills = list(reader)

    if not skills:
        print("No skills evaluated yet.")
        return

    total = len(skills)

    # Grade distribution
    grades = Counter(s['grade'] for s in skills)

    # Recommendation distribution
    recommendations = Counter(s['recommendation'] for s in skills)

    # Score statistics
    scores = [float(s['final_score']) for s in skills if s['final_score'] != 'ERROR']
    static_scores = [float(s['static_score']) for s in skills if s['static_score'] != '0']
    security_scores = [float(s['security_score']) for s in skills if s['security_score'] != '0']

    # Print summary
    print(f"Total Skills Evaluated: {total}")
    print()

    print("Grade Distribution:")
    print("-" * 40)
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grades.get(grade, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = '█' * int(pct / 5)
        print(f"  {grade}: {count:3d} ({pct:5.1f}%) {bar}")
    print()

    print("Recommendations:")
    print("-" * 40)
    for rec, count in recommendations.most_common():
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {rec:20s}: {count:3d} ({pct:5.1f}%)")
    print()

    if scores:
        print("Score Statistics:")
        print("-" * 40)
        print(f"  Final Score:")
        print(f"    Mean:   {sum(scores)/len(scores):6.1f}/100")
        print(f"    Min:    {min(scores):6.1f}/100")
        print(f"    Max:    {max(scores):6.1f}/100")
        print()
        print(f"  Static Tests:")
        print(f"    Mean:   {sum(static_scores)/len(static_scores):6.1f}/100")
        print()
        print(f"  Security:")
        print(f"    Mean:   {sum(security_scores)/len(security_scores):6.1f}/100")
        print()

    # Top performers
    print("Top 5 Skills:")
    print("-" * 40)
    sorted_skills = sorted(
        [s for s in skills if s['final_score'] != 'ERROR'],
        key=lambda x: float(x['final_score']),
        reverse=True
    )[:5]
    for i, skill in enumerate(sorted_skills, 1):
        print(f"  {i}. {skill['skill_name']:30s} {float(skill['final_score']):5.1f} ({skill['grade']})")
    print()

    # Bottom performers
    print("Bottom 5 Skills:")
    print("-" * 40)
    bottom_skills = sorted(
        [s for s in skills if s['final_score'] != 'ERROR'],
        key=lambda x: float(x['final_score'])
    )[:5]
    for i, skill in enumerate(bottom_skills, 1):
        print(f"  {i}. {skill['skill_name']:30s} {float(skill['final_score']):5.1f} ({skill['grade']})")
    print()

    # Security issues
    print("Security Concerns (score < 80):")
    print("-" * 40)
    security_issues = [
        s for s in skills
        if s['security_score'] != 'ERROR' and float(s['security_score']) < 80
    ]
    if security_issues:
        for skill in sorted(security_issues, key=lambda x: float(x['security_score'])):
            print(f"  {skill['skill_name']:30s} {float(skill['security_score']):5.1f}/100")
    else:
        print("  ✅ No security concerns!")
    print()

    # Detailed findings
    print("Detailed Findings (skills with issues):")
    print("-" * 70)
    for skill_name in sorted(s['skill_name'] for s in skills):
        skill_dir = results_dir / skill_name
        report_files = list(skill_dir.glob("*.json"))

        if not report_files:
            continue

        with open(report_files[0]) as f:
            data = json.load(f)

        # Check for issues
        has_issues = False

        # Static test issues
        if data.get('pillar_scores', {}).get('static_tests', {}).get('score', 100) < 100:
            if not has_issues:
                print(f"\n{skill_name}:")
                has_issues = True
            # Would need to access detailed static test results here

        # Security findings
        # Would need to access detailed security results here

    print()
    print("="*70)
    print(f"Full results: {results_dir}")
    print("="*70)


if __name__ == "__main__":
    results_dir = Path("./batch_results")
    analyze_results(results_dir)
