#!/usr/bin/env python3
"""
Enhanced detailed console report generator with comprehensive explanations.
"""

import sys
import json
from pathlib import Path
from typing import Dict, List


class EnhancedReportGenerator:
    """Generate comprehensive console reports with full details."""

    def __init__(self):
        self.width = 100

    def generate(self, summary_csv: str):
        """Generate enhanced report from summary CSV."""

        print("=" * self.width)
        print("RED HAT SKILL EVALUATION FRAMEWORK (SkillEval) v3.0")
        print("COMPREHENSIVE EVALUATION REPORT")
        print("=" * self.width)
        print()

        # Read summary
        summary = self._read_summary(summary_csv)

        # Executive summary
        self._print_executive_summary(summary)

        # Detailed skill results
        print()
        print("=" * self.width)
        print("DETAILED SKILL RESULTS")
        print("=" * self.width)
        print()

        for skill_data in summary:
            if skill_data.get('recommendation') != 'NO_REPORT':
                self._print_skill_details(skill_data)

    def _read_summary(self, csv_path: str) -> List[Dict]:
        """Read summary CSV and load detailed reports."""
        summary = []

        with open(csv_path) as f:
            lines = f.readlines()[1:]  # Skip header

        for line in lines:
            parts = line.strip().split(',')
            if len(parts) < 6:
                continue

            skill_name = parts[0]

            # Try to load detailed JSON report
            report_path = Path(csv_path).parent / skill_name / f"{skill_name}_report.json"

            if report_path.exists():
                with open(report_path) as f:
                    report_data = json.load(f)
                summary.append(report_data)
            else:
                # Fallback to CSV data
                summary.append({
                    'skill_name': skill_name,
                    'final_score': parts[1],
                    'grade': parts[2],
                    'recommendation': parts[5],
                })

        return summary

    def _print_executive_summary(self, summary: List[Dict]):
        """Print executive summary section."""
        total = len(summary)

        # Grade distribution
        grades = {'A': 0, 'B': 0, 'C': 0, 'D': 0, 'F': 0}
        for s in summary:
            grade = s.get('grade', 'F')
            if grade in grades:
                grades[grade] += 1

        # Recommendations
        recs = {'APPROVE': 0, 'CONDITIONAL': 0, 'REJECT': 0}
        for s in summary:
            rec = s.get('recommendation', '')
            if 'APPROVE' in rec:
                recs['APPROVE'] += 1
            elif 'CONDITIONAL' in rec:
                recs['CONDITIONAL'] += 1
            elif 'REJECT' in rec:
                recs['REJECT'] += 1

        # Scores
        scores = [float(s.get('final_score', 0)) for s in summary if s.get('final_score', 'ERROR') != 'ERROR']

        print("EXECUTIVE SUMMARY")
        print("-" * self.width)
        print(f"Total Skills Evaluated: {total}")
        print()
        print("Grade Distribution:")
        for grade, count in grades.items():
            pct = (count / total * 100) if total > 0 else 0
            bar = '█' * int(pct / 2)
            print(f"  {grade}:   {count:2d} ({pct:5.1f}%) {bar}")
        print()
        print("Recommendations:")
        print(f"  ✅ APPROVE:       {recs['APPROVE']:2d} ({recs['APPROVE']/total*100:5.1f}%)")
        print(f"  ⚠️  CONDITIONAL:   {recs['CONDITIONAL']:2d} ({recs['CONDITIONAL']/total*100:5.1f}%)")
        print(f"  ❌ REJECT:        {recs['REJECT']:2d} ({recs['REJECT']/total*100:5.1f}%)")
        print()

        if scores:
            print("Score Statistics:")
            print(f"  Mean:     {sum(scores)/len(scores):5.1f}/100")
            print(f"  Median:   {sorted(scores)[len(scores)//2]:5.1f}/100")
            print(f"  Min:      {min(scores):5.1f}/100")
            print(f"  Max:      {max(scores):5.1f}/100")

    def _print_skill_details(self, skill_data: Dict):
        """Print detailed skill report."""
        skill_name = skill_data.get('skill_name', 'Unknown')
        final_score = skill_data.get('final_score', 0)
        grade = skill_data.get('grade', 'F')
        recommendation = skill_data.get('recommendation', '')

        # Header
        icon = "✅" if "APPROVE" in recommendation else "⚠️" if "CONDITIONAL" in recommendation else "❌"
        print(f"{icon} {skill_name.upper()}")
        print("-" * self.width)
        print(f"Score:          {final_score}/100 ({grade})")
        print(f"Recommendation: {recommendation}")
        print()

        # Overall explanation
        if 'metadata' in skill_data and 'overall_explanation' in skill_data['metadata']:
            print("SCORE EXPLANATION:")
            print(skill_data['metadata']['overall_explanation'])
            print()

        # Pillar scores
        pillar_scores = skill_data.get('pillar_scores', {})

        print("Pillar Scores:")
        for pillar_name in ['static_tests', 'security', 'harness']:
            if pillar_name not in pillar_scores:
                continue

            pillar = pillar_scores[pillar_name]
            score = pillar.get('score', 0)
            p_grade = pillar.get('grade', 'F')
            weight = pillar.get('weight', 0)

            icon = "✅" if p_grade in ['A', 'B'] else "⚠️" if p_grade == 'C' else "❌"
            print(f"  {icon} {pillar_name.replace('_', ' ').title():18s}: {score:6.1f}/100 ({p_grade}) - weight {weight:.0%}")

            # Details and explanation
            if 'details' in pillar and 'explanation' in pillar['details']:
                print(f"     {pillar['details']['explanation']}")
                print()

        # Security findings (detailed)
        if 'security' in pillar_scores and 'findings' in pillar_scores['security']:
            findings = pillar_scores['security']['findings']
            if findings:
                print()
                print(f"  SECURITY FINDINGS ({len(findings)} total):")
                print()

                # Group by severity
                by_severity = {}
                for f in findings:
                    sev = f['severity']
                    if sev not in by_severity:
                        by_severity[sev] = []
                    by_severity[sev].append(f)

                # Print by severity
                for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
                    if sev not in by_severity:
                        continue

                    sev_findings = by_severity[sev]
                    emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡', 'LOW': '🔵', 'INFO': '⚪'}[sev]

                    print(f"    {emoji} {sev}: {len(sev_findings)} finding(s)")

                    for i, f in enumerate(sev_findings, 1):
                        print(f"      {i}. {f['type']}")
                        print(f"         Message: {f['message']}")
                        location = f"{f['file']}:{f['line']}" if f.get('line') else f.get('file', 'N/A')
                        print(f"         Location: {location}")
                        print(f"         Remediation: {f.get('remediation', 'N/A')}")
                        print()

        # Harness functional results (detailed)
        if 'harness' in pillar_scores and 'details' in pillar_scores['harness']:
            details = pillar_scores['harness']['details']

            if 'functional_results' in details and details['functional_results']:
                print()
                print("  HARNESS FUNCTIONAL RESULTS:")
                print()

                for fr in details['functional_results']:
                    icon = "✅" if fr.get('passed') else "❌"
                    print(f"    {icon} {fr.get('grader_name', 'Unknown')}: {fr.get('score', 0):.1f}/100")
                    print(f"       Result: {fr.get('result', 'No result')}")
                    if fr.get('output'):
                        print(f"       Output: {fr.get('output')[:200]}...")
                print()

            if 'safety_checks' in details and details['safety_checks']:
                print()
                print("  SAFETY CHECKS:")
                print()

                for sc in details['safety_checks']:
                    score = sc.get('score', 0)
                    icon = "✅" if score == 100 else "⚠️"
                    print(f"    {icon} {sc.get('check', 'Unknown')}: {score:.1f}/100 ({sc.get('severity', 'N/A')})")
                    print(f"       {sc.get('details', 'No details')}")
                print()

        print()
        print()


def main():
    if len(sys.argv) < 2:
        print("Usage: python enhanced_report.py <summary.csv>")
        sys.exit(1)

    generator = EnhancedReportGenerator()
    generator.generate(sys.argv[1])


if __name__ == "__main__":
    main()
