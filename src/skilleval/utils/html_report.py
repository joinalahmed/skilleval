"""
HTML report generator.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any


def generate_html_report(report_data: Dict[str, Any], output_path: Path) -> None:
    """
    Generate HTML report from evaluation results.

    Args:
        report_data: The FinalReport as dict
        output_path: Path to save HTML file
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkillEval Report - {report_data['skill_name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'SkillEval Display', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            line-height: 1.6;
            color: #151515;
            background: #f5f5f5;
            padding: 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #EE0000 0%, #C40000 100%);
            color: white;
            padding: 40px;
        }}

        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .header .subtitle {{
            opacity: 0.9;
            font-size: 14px;
        }}

        .score-card {{
            display: flex;
            justify-content: space-around;
            padding: 40px;
            background: #f8f8f8;
            border-bottom: 1px solid #e0e0e0;
        }}

        .score-item {{
            text-align: center;
        }}

        .score-value {{
            font-size: 48px;
            font-weight: 700;
            margin-bottom: 10px;
        }}

        .score-label {{
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .grade-A {{ color: #2E7D32; }}
        .grade-B {{ color: #1976D2; }}
        .grade-C {{ color: #F57C00; }}
        .grade-D {{ color: #E64A19; }}
        .grade-F {{ color: #C62828; }}

        .recommendation {{
            padding: 20px 40px;
            background: #FFF3CD;
            border-left: 4px solid #FFC107;
            margin: 20px 40px;
            border-radius: 4px;
        }}

        .recommendation.approve {{
            background: #D4EDDA;
            border-left-color: #28A745;
        }}

        .recommendation.reject {{
            background: #F8D7DA;
            border-left-color: #DC3545;
        }}

        .section {{
            padding: 40px;
        }}

        .section h2 {{
            font-size: 24px;
            margin-bottom: 20px;
            color: #151515;
            border-bottom: 2px solid #EE0000;
            padding-bottom: 10px;
        }}

        .pillar-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }}

        .pillar-card {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 20px;
            background: white;
        }}

        .pillar-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}

        .pillar-name {{
            font-size: 18px;
            font-weight: 600;
            text-transform: capitalize;
        }}

        .pillar-grade {{
            font-size: 24px;
            font-weight: 700;
        }}

        .pillar-score {{
            font-size: 14px;
            color: #666;
            margin-bottom: 10px;
        }}

        .progress-bar {{
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #1976D2 0%, #2196F3 100%);
            transition: width 0.3s ease;
        }}

        .findings {{
            margin-top: 20px;
        }}

        .finding {{
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid;
            border-radius: 4px;
            background: #f8f8f8;
        }}

        .finding.critical {{ border-left-color: #C62828; background: #FFEBEE; }}
        .finding.high {{ border-left-color: #E64A19; background: #FBE9E7; }}
        .finding.medium {{ border-left-color: #F57C00; background: #FFF3E0; }}
        .finding.low {{ border-left-color: #1976D2; background: #E3F2FD; }}

        .finding-header {{
            font-weight: 600;
            margin-bottom: 5px;
        }}

        .finding-location {{
            font-size: 12px;
            color: #666;
            font-family: 'Courier New', monospace;
        }}

        .finding-remediation {{
            margin-top: 10px;
            padding: 10px;
            background: white;
            border-radius: 4px;
            font-size: 14px;
        }}

        .metadata {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
            padding: 20px;
            background: #f8f8f8;
            border-radius: 4px;
        }}

        .metadata-item {{
            padding: 10px;
        }}

        .metadata-label {{
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 5px;
        }}

        .metadata-value {{
            font-size: 14px;
            font-weight: 600;
        }}

        .footer {{
            padding: 20px 40px;
            background: #f8f8f8;
            text-align: center;
            color: #666;
            font-size: 12px;
            border-top: 1px solid #e0e0e0;
        }}

        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .badge.critical {{ background: #FFEBEE; color: #C62828; }}
        .badge.high {{ background: #FBE9E7; color: #E64A19; }}
        .badge.medium {{ background: #FFF3E0; color: #F57C00; }}
        .badge.low {{ background: #E3F2FD; color: #1976D2; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>SkillEval Skill Evaluation Framework</h1>
            <div class="subtitle">Evaluation Report: {report_data['skill_name']}</div>
            <div class="subtitle">Generated: {datetime.fromisoformat(report_data['evaluation_date'].replace('Z', '+00:00')).strftime('%B %d, %Y at %H:%M:%S')}</div>
        </div>

        <!-- Score Card -->
        <div class="score-card">
            <div class="score-item">
                <div class="score-value grade-{report_data['grade']}">{report_data['final_score']:.1f}</div>
                <div class="score-label">Final Score</div>
            </div>
            <div class="score-item">
                <div class="score-value grade-{report_data['grade']}">{report_data['grade']}</div>
                <div class="score-label">Grade</div>
            </div>
        </div>

        <!-- Recommendation -->
        <div class="recommendation {'approve' if 'APPROVE' in report_data['recommendation'] else 'reject' if 'REJECT' in report_data['recommendation'] else ''}">
            <strong>Recommendation:</strong> {report_data['recommendation']}
        </div>

        <!-- Pillar Scores -->
        <div class="section">
            <h2>Pillar Breakdown</h2>
            <div class="pillar-grid">
                {generate_pillar_cards(report_data['pillar_scores'])}
            </div>
        </div>

        <!-- Security Findings -->
        {generate_security_findings(report_data['pillar_scores'])}

        <!-- Metadata -->
        <div class="section">
            <h2>Evaluation Metadata</h2>
            <div class="metadata">
                <div class="metadata-item">
                    <div class="metadata-label">Framework Version</div>
                    <div class="metadata-value">{report_data['framework_version']}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Deterministic</div>
                    <div class="metadata-value">{'Yes' if report_data['deterministic'] else 'No'}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Run-to-Run Variance</div>
                    <div class="metadata-value">{report_data['run_to_run_variance']}</div>
                </div>
                <div class="metadata-item">
                    <div class="metadata-label">Duration</div>
                    <div class="metadata-value">{report_data['total_duration_seconds']:.3f}s</div>
                </div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            SkillEval Skill Evaluation Framework (SkillEval) v{report_data['framework_version']}<br>
            100% Deterministic Evaluation • No LLM Judges • Reproducible Results
        </div>
    </div>
</body>
</html>
"""

    output_path.write_text(html)


def generate_pillar_cards(pillar_scores: Dict[str, Any]) -> str:
    """Generate HTML for pillar cards."""
    cards = []

    for pillar_name, pillar_data in pillar_scores.items():
        score = pillar_data['score']
        grade = pillar_data['grade']
        weight = pillar_data.get('weight', 0) * 100

        # Calculate progress bar width
        progress = min(100, max(0, score))

        card = f"""
                <div class="pillar-card">
                    <div class="pillar-header">
                        <div class="pillar-name">{pillar_name.replace('_', ' ')}</div>
                        <div class="pillar-grade grade-{grade}">{grade}</div>
                    </div>
                    <div class="pillar-score">{score:.1f}/100 (Weight: {weight:.0f}%)</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {progress}%"></div>
                    </div>
                </div>
        """
        cards.append(card)

    return '\n'.join(cards)


def generate_security_findings(pillar_scores: Dict[str, Any]) -> str:
    """Generate HTML for security findings section."""
    security = pillar_scores.get('security', {})
    findings = security.get('findings', [])

    if not findings:
        return ""

    findings_html = []
    for finding in findings:
        severity = finding['severity'].lower()

        location = ""
        if finding.get('file'):
            location = f"<div class='finding-location'>{finding['file']}"
            if finding.get('line'):
                location += f":{finding['line']}"
            location += "</div>"

        remediation = ""
        if finding.get('remediation'):
            remediation = f"<div class='finding-remediation'><strong>Remediation:</strong> {finding['remediation']}</div>"

        finding_html = f"""
                <div class="finding {severity}">
                    <div class="finding-header">
                        <span class="badge {severity}">{finding['severity']}</span>
                        {finding['type']}: {finding['message']}
                    </div>
                    {location}
                    {remediation}
                </div>
        """
        findings_html.append(finding_html)

    return f"""
        <div class="section">
            <h2>Security Findings ({len(findings)})</h2>
            <div class="findings">
                {''.join(findings_html)}
            </div>
        </div>
    """
