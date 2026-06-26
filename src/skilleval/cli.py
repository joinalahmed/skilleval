"""
Command-line interface for SkillEval.
"""

import sys
import json
from pathlib import Path
from typing import Optional

import click

from skilleval import __version__
from skilleval.config import load_config
from skilleval.orchestrator import Orchestrator
from skilleval.utils.logger import setup_logging, logger


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to config file",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path], verbose: bool):
    """
    SkillEval Skill Evaluation Framework (SkillEval)

    100% deterministic evaluation for AI agent skills.
    """
    # Load configuration
    cfg = load_config(config)

    # Setup logging
    level = "DEBUG" if verbose else cfg.logging_level
    setup_logging(level=level, format_style=cfg.logging_format)

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg
    ctx.obj["verbose"] = verbose


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output directory")
@click.pass_context
def eval(ctx: click.Context, skill_path: Path, output: Optional[Path]):
    """
    Run full evaluation on a skill.

    Example:
        skilleval eval /path/to/skill
    """
    config = ctx.obj["config"]

    logger.info(f"Evaluating skill: {skill_path}")
    logger.info(f"Framework version: {__version__}")

    orchestrator = Orchestrator(config)

    try:
        result = orchestrator.evaluate(skill_path)

        # Determine output path
        if output:
            output_dir = output
        else:
            output_dir = Path(config.output_directory)

        output_dir.mkdir(parents=True, exist_ok=True)

        # Write JSON report
        report_path = output_dir / f"{result.final_report.skill_name}_report.json"
        with open(report_path, "w") as f:
            json.dump(result.final_report.model_dump(mode="json"), f, indent=2, default=str)

        logger.info(f"Report saved to: {report_path}")

        # Write HTML report if enabled
        if config.output_format in ["html", "both"]:
            from skilleval.utils.html_report import generate_html_report
            html_path = output_dir / f"{result.final_report.skill_name}_report.html"
            generate_html_report(result.final_report.model_dump(mode="json"), html_path)
            logger.info(f"HTML report saved to: {html_path}")

        # Print summary
        click.echo("\n" + "="*60)
        click.echo(f"SKILL: {result.final_report.skill_name}")
        click.echo(f"SCORE: {result.final_report.final_score:.1f}/100")
        click.echo(f"GRADE: {result.final_report.grade.value}")
        click.echo(f"RECOMMENDATION: {result.final_report.recommendation}")
        click.echo("="*60)
        click.echo(f"\nPillar Scores:")
        for pillar, score_data in result.final_report.pillar_scores.items():
            if isinstance(score_data, dict):
                score = score_data.get("score", 0)
                grade = score_data.get("grade", "N/A")
            else:
                score = score_data
                grade = "N/A"
            click.echo(f"  {pillar:20s}: {score:5.1f}/100 ({grade})")
        click.echo(f"\nDuration: {result.final_report.total_duration_seconds:.1f}s")
        click.echo(f"Report: {report_path}\n")

        # Exit code based on recommendation
        if "REJECT" in result.final_report.recommendation:
            sys.exit(1)
        elif "CONDITIONAL" in result.final_report.recommendation:
            sys.exit(0)  # Pass but with warnings
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        sys.exit(2)


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def static(ctx: click.Context, skill_path: Path):
    """
    Run only static tests pillar.

    Example:
        skilleval static /path/to/skill
    """
    config = ctx.obj["config"]

    logger.info(f"Running static tests: {skill_path}")

    from skilleval.pillars.static_tests import StaticTestsPillar

    pillar = StaticTestsPillar(config.static_tests)
    result = pillar.run(skill_path)

    click.echo(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def security(ctx: click.Context, skill_path: Path):
    """
    Run only security pillar.

    Example:
        skilleval security /path/to/skill
    """
    config = ctx.obj["config"]

    logger.info(f"Running security scan: {skill_path}")

    from skilleval.pillars.security import SecurityPillar

    pillar = SecurityPillar(config.security)
    result = pillar.run(skill_path)

    click.echo(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.pass_context
def harness(ctx: click.Context, skill_path: Path):
    """
    Run only harness evaluation pillar.

    Example:
        skilleval harness /path/to/skill
    """
    config = ctx.obj["config"]

    logger.info(f"Running harness evaluation: {skill_path}")

    from skilleval.pillars.harness import HarnessPillar

    pillar = HarnessPillar(config.harness)

    # Load skill first
    from skilleval.utils.skill_loader import load_skill
    skill = load_skill(skill_path)

    result = pillar.run(skill)

    click.echo(json.dumps(result.model_dump(mode="json"), indent=2, default=str))


@cli.command()
@click.argument("skill_path", type=click.Path(exists=True, path_type=Path))
@click.option("--min-score", type=int, default=75, help="Minimum score to pass")
@click.option("--max-cost", type=float, help="Maximum cost in USD")
@click.option("--max-tokens", type=int, default=50000, help="Maximum tokens")
@click.option("--exit-on-fail/--no-exit-on-fail", default=True)
@click.pass_context
def ci(
    ctx: click.Context,
    skill_path: Path,
    min_score: int,
    max_cost: Optional[float],
    max_tokens: int,
    exit_on_fail: bool,
):
    """
    CI/CD mode with strict thresholds.

    Example:
        skilleval ci /path/to/skill --min-score 75 --exit-on-fail
    """
    config = ctx.obj["config"]

    logger.info(f"CI mode: {skill_path}")
    logger.info(f"Thresholds: score>={min_score}, tokens<={max_tokens}")

    orchestrator = Orchestrator(config)
    result = orchestrator.evaluate(skill_path)

    passed = True
    reasons = []

    # Check score
    if result.final_report.final_score < min_score:
        passed = False
        reasons.append(f"Score {result.final_report.final_score:.1f} < {min_score}")

    # Check for critical findings
    if result.security and result.security.has_critical:
        passed = False
        reasons.append("Critical security findings detected")

    # Check tokens if harness ran
    if result.harness:
        # Extract total tokens from safety checks
        for check in result.harness.safety_checks:
            if check.check == "cost_tracking":
                total_tokens = check.details.get("total_tokens", 0)
                if total_tokens > max_tokens:
                    passed = False
                    reasons.append(f"Tokens {total_tokens} > {max_tokens}")

    # Print result
    if passed:
        click.secho("✓ PASS", fg="green", bold=True)
        click.echo(f"  Score: {result.final_report.final_score:.1f}/100")
        sys.exit(0)
    else:
        click.secho("✗ FAIL", fg="red", bold=True)
        click.echo(f"  Score: {result.final_report.final_score:.1f}/100")
        for reason in reasons:
            click.echo(f"  - {reason}")

        if exit_on_fail:
            sys.exit(1)
        else:
            sys.exit(0)


@cli.command()
def doctor():
    """
    Check dependencies and environment.

    Example:
        skilleval doctor
    """
    click.echo("Checking SkillEval dependencies...\n")

    checks = []

    # Python version
    import sys
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    checks.append(("Python", py_version, py_version >= "3.10", ">=3.10 required"))

    # Podman
    try:
        import podman
        checks.append(("podman-py", podman.__version__, True, "Installed"))
    except ImportError:
        checks.append(("podman-py", "N/A", False, "Not installed"))

    # PyYAML
    try:
        import yaml
        checks.append(("PyYAML", "installed", True, "Installed"))
    except ImportError:
        checks.append(("PyYAML", "N/A", False, "Not installed"))

    # Pydantic
    try:
        import pydantic
        checks.append(("Pydantic", pydantic.__version__, True, "Installed"))
    except ImportError:
        checks.append(("Pydantic", "N/A", False, "Not installed"))

    # Optional: pip-audit
    try:
        import subprocess
        result = subprocess.run(["pip-audit", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append(("pip-audit", "installed", True, "Installed (optional)"))
        else:
            checks.append(("pip-audit", "N/A", False, "Not installed (optional)"))
    except FileNotFoundError:
        checks.append(("pip-audit", "N/A", False, "Not installed (optional)"))

    # Print results
    for name, version, status, note in checks:
        icon = "✓" if status else "✗"
        color = "green" if status else "red"
        click.secho(f"{icon} {name:20s} {version:15s} {note}", fg=color)

    # Summary
    total = len(checks)
    passed = sum(1 for _, _, status, _ in checks if status)

    click.echo(f"\n{passed}/{total} checks passed")

    if passed < total:
        sys.exit(1)


@cli.command()
@click.option("--show", is_flag=True, help="Show current config")
@click.option("--init", is_flag=True, help="Create default config")
@click.option("--validate", is_flag=True, help="Validate config file")
def config(show: bool, init: bool, validate: bool):
    """
    Configuration management.

    Example:
        skilleval config --show
        skilleval config --init
    """
    if show:
        from skilleval.config import load_config
        cfg = load_config()
        click.echo(cfg.model_dump_json(indent=2))

    elif init:
        config_path = Path.home() / ".skilleval" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)

        if config_path.exists():
            if not click.confirm(f"Config exists at {config_path}. Overwrite?"):
                return

        from skilleval.config import create_default_config
        create_default_config(config_path)
        click.echo(f"Created default config at: {config_path}")

    elif validate:
        from skilleval.config import load_config
        try:
            cfg = load_config()
            click.secho("✓ Config is valid", fg="green")
        except Exception as e:
            click.secho(f"✗ Config validation failed: {e}", fg="red")
            sys.exit(1)

    else:
        click.echo("Use --show, --init, or --validate")


def main():
    """Entry point."""
    cli(obj={})


if __name__ == "__main__":
    main()
