#!/usr/bin/env python3
"""
Generate detailed HTML-like report from batch evaluation results.
"""

import json
import csv
from pathlib import Path
from collections import Counter


def generate_detailed_report(results_dir: Path):
    """Generate detailed report with findings."""

    print("="*80)
    print("RED HAT SKILL EVALUATION FRAMEWORK (SkillEval)")
    print("Batch Evaluation Report")
    print("="*80)
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

    # Print executive summary
    print("EXECUTIVE SUMMARY")
    print("-"*80)
    print(f"Total Skills Evaluated: {total}")
    print()

    # Grade distribution
    grades = Counter(s['grade'] for s in skills)
    print("Grade Distribution:")
    for grade in ['A', 'B', 'C', 'D', 'F']:
        count = grades.get(grade, 0)
        pct = (count / total * 100) if total > 0 else 0
        bar = '█' * int(pct / 2)
        print(f"  {grade}: {count:3d} ({pct:5.1f}%) {bar}")
    print()

    # Recommendation distribution
    recommendations = Counter(s['recommendation'] for s in skills)
    approve = recommendations.get('APPROVE', 0)
    conditional = recommendations.get('CONDITIONAL', 0)
    reject = sum(v for k, v in recommendations.items() if 'REJECT' in k)

    print("Recommendations:")
    print(f"  ✅ APPROVE:     {approve:3d} ({approve/total*100:5.1f}%)")
    print(f"  ⚠️  CONDITIONAL: {conditional:3d} ({conditional/total*100:5.1f}%)")
    print(f"  ❌ REJECT:      {reject:3d} ({reject/total*100:5.1f}%)")
    print()

    # Score statistics
    scores = [float(s['final_score']) for s in skills if s['final_score'] != 'ERROR']
    if scores:
        print("Score Statistics:")
        print(f"  Mean:   {sum(scores)/len(scores):6.1f}/100")
        print(f"  Median: {sorted(scores)[len(scores)//2]:6.1f}/100")
        print(f"  Min:    {min(scores):6.1f}/100")
        print(f"  Max:    {max(scores):6.1f}/100")
    print()

    # Detailed per-skill results
    print("="*80)
    print("DETAILED SKILL RESULTS")
    print("="*80)
    print()

    for skill_name in sorted(s['skill_name'] for s in skills):
        skill_dir = results_dir / skill_name
        report_files = list(skill_dir.glob("*.json"))

        if not report_files:
            print(f"❌ {skill_name}: NO REPORT GENERATED")
            print()
            continue

        with open(report_files[0]) as f:
            data = json.load(f)

        # Skill header
        score = data['final_score']
        grade = data['grade']
        rec = data['recommendation']

        # Emoji for grade
        if grade == 'A':
            grade_emoji = '🏆'
        elif grade == 'B':
            grade_emoji = '✅'
        elif grade == 'C':
            grade_emoji = '⚠️'
        elif grade == 'D':
            grade_emoji = '⚠️'
        else:
            grade_emoji = '❌'

        print(f"{grade_emoji} {skill_name.upper()}")
        print("-"*80)
        print(f"Score:          {score:.1f}/100 ({grade})")
        print(f"Recommendation: {rec}")
        print()

        # Pillar scores
        print("Pillar Scores:")
        for pillar, info in data['pillar_scores'].items():
            pillar_score = info['score']
            pillar_grade = info['grade']
            pillar_weight = info['weight']

            # Emoji for pillar
            if pillar_grade == 'A':
                p_emoji = '✅'
            elif pillar_grade in ['B', 'C']:
                p_emoji = '⚠️'
            else:
                p_emoji = '❌'

            print(f"  {p_emoji} {pillar:20s}: {pillar_score:5.1f}/100 ({pillar_grade}) - weight {pillar_weight*100:.0f}%")
        print()

        # Static test issues
        if 'issues' in data['pillar_scores'].get('static_tests', {}):
            issues = data['pillar_scores']['static_tests']['issues']
            if issues:
                print(f"  Static Test Issues ({len(issues)}):")
                for issue in issues:
                    print(f"    • {issue}")
                print()

        # Security findings
        if 'findings' in data['pillar_scores'].get('security', {}):
            findings = data['pillar_scores']['security']['findings']
            if findings:
                print(f"  Security Findings ({len(findings)}):")

                # Group by severity
                by_severity = {}
                for f in findings:
                    sev = f['severity']
                    if sev not in by_severity:
                        by_severity[sev] = []
                    by_severity[sev].append(f)

                # Print by severity
                for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']:
                    if severity not in by_severity:
                        continue

                    sev_findings = by_severity[severity]
                    if severity == 'CRITICAL':
                        sev_emoji = '🔴'
                    elif severity == 'HIGH':
                        sev_emoji = '🟠'
                    elif severity == 'MEDIUM':
                        sev_emoji = '🟡'
                    else:
                        sev_emoji = '🔵'

                    print(f"    {sev_emoji} {severity}: {len(sev_findings)} finding(s)")

                    for f in sev_findings[:3]:  # Show first 3 per severity
                        print(f"      • {f['type']}: {f['message']}")
                        if f.get('file'):
                            location = f['file']
                            if f.get('line'):
                                location += f":{f['line']}"
                            print(f"        Location: {location}")
                        if f.get('remediation'):
                            print(f"        Fix: {f['remediation']}")

                    if len(sev_findings) > 3:
                        print(f"      ... and {len(sev_findings)-3} more")

                print()

        # Summary stats
        if 'by_severity' in data['pillar_scores'].get('security', {}):
            by_sev = data['pillar_scores']['security']['by_severity']
            has_critical = data['pillar_scores']['security'].get('has_critical', False)
            has_high = data['pillar_scores']['security'].get('has_high', False)

            if has_critical or has_high:
                print(f"  ⚠️  Security Summary:")
                if has_critical:
                    print(f"     🔴 CRITICAL issues found: {by_sev.get('CRITICAL', 0)}")
                if has_high:
                    print(f"     🟠 HIGH issues found: {by_sev.get('HIGH', 0)}")
                print()

        print()

    # Security summary across all skills
    print("="*80)
    print("SECURITY SUMMARY ACROSS ALL SKILLS")
    print("="*80)
    print()

    total_findings = 0
    total_critical = 0
    total_high = 0
    total_medium = 0
    total_low = 0

    for skill_name in sorted(s['skill_name'] for s in skills):
        skill_dir = results_dir / skill_name
        report_files = list(skill_dir.glob("*.json"))
        if not report_files:
            continue

        with open(report_files[0]) as f:
            data = json.load(f)

        if 'by_severity' in data['pillar_scores'].get('security', {}):
            by_sev = data['pillar_scores']['security']['by_severity']
            total_critical += by_sev.get('CRITICAL', 0)
            total_high += by_sev.get('HIGH', 0)
            total_medium += by_sev.get('MEDIUM', 0)
            total_low += by_sev.get('LOW', 0)

    total_findings = total_critical + total_high + total_medium + total_low

    print(f"Total Findings: {total_findings}")
    print(f"  🔴 CRITICAL: {total_critical}")
    print(f"  🟠 HIGH:     {total_high}")
    print(f"  🟡 MEDIUM:   {total_medium}")
    print(f"  🔵 LOW:      {total_low}")
    print()

    # Top recommendations
    print("="*80)
    print("TOP RECOMMENDATIONS")
    print("="*80)
    print()

    # Skills needing immediate attention (CRITICAL/HIGH security)
    needs_attention = []
    for skill_name in sorted(s['skill_name'] for s in skills):
        skill_dir = results_dir / skill_name
        report_files = list(skill_dir.glob("*.json"))
        if not report_files:
            continue

        with open(report_files[0]) as f:
            data = json.load(f)

        if data['pillar_scores'].get('security', {}).get('has_critical') or \
           data['pillar_scores'].get('security', {}).get('has_high'):
            needs_attention.append((skill_name, data))

    if needs_attention:
        print("⚠️  Skills Needing Immediate Attention (CRITICAL/HIGH security):")
        for skill_name, data in needs_attention:
            score = data['final_score']
            grade = data['grade']
            by_sev = data['pillar_scores']['security'].get('by_severity', {})
            print(f"  • {skill_name} ({score:.1f}, {grade})")
            if by_sev.get('CRITICAL'):
                print(f"    🔴 {by_sev['CRITICAL']} CRITICAL issue(s)")
            if by_sev.get('HIGH'):
                print(f"    🟠 {by_sev['HIGH']} HIGH issue(s)")
        print()

    # Top performers
    sorted_skills = sorted(
        [s for s in skills if s['final_score'] != 'ERROR'],
        key=lambda x: float(x['final_score']),
        reverse=True
    )[:3]

    if sorted_skills:
        print("🏆 Top Performers:")
        for skill in sorted_skills:
            print(f"  • {skill['skill_name']:30s} {float(skill['final_score']):5.1f} ({skill['grade']})")
        print()

    print("="*80)
    print(f"Full results: {results_dir}")
    print("="*80)


if __name__ == "__main__":
    results_dir = Path("./batch_results")
    generate_detailed_report(results_dir)
