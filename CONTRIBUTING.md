# Contributing to SkillEval

Thank you for your interest in contributing to the Skill Evaluation Framework!

## Code of Conduct

This project adheres to the Contributor Covenant Code of Conduct. By participating, you are expected to uphold this code.

## How to Contribute

### Reporting Bugs

- Search existing issues to avoid duplicates
- Use the bug report template
- Include steps to reproduce, expected behavior, and actual behavior
- Add relevant labels and screenshots if applicable

### Suggesting Features

- Check if the feature has already been requested
- Use the feature request template
- Describe the use case and expected behavior
- Explain why this feature would be useful

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following our coding standards
3. **Add tests** for any new functionality
4. **Update documentation** if you change APIs or behavior
5. **Run the test suite** to ensure nothing breaks
6. **Submit a pull request** with a clear description

## Development Setup

```bash
# Clone the repository
git clone https://github.com/skilleval/skilleval.git
cd skilleval

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install in development mode
pip install -e .

# Run tests
pytest tests/

# Run linting
ruff check src/
mypy src/
```

## Coding Standards

### Python Code Style

- Follow PEP 8
- Use type hints for all functions
- Maximum line length: 100 characters
- Use `ruff` for linting
- Use `mypy` for type checking

### Documentation

- Docstrings for all public functions/classes (Google style)
- Update README.md for user-facing changes
- Add examples for new features

### Testing

- Write unit tests for all new code
- Integration tests for pillar interactions
- Aim for >80% code coverage
- Use descriptive test names: `test_<what>_<condition>_<expected>`

### Commit Messages

Follow conventional commits:

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(security): add Layer 2 SkillSpector integration

Integrate SkillSpector for advanced AST analysis and YARA pattern
matching. Adds 64 additional security checks.

Closes #42
```

## Project Structure

```
skilleval/
├── src/skilleval/          # Source code
│   ├── models_phase1.py      # Phase 1 data models
│   ├── models_phase2.py      # Phase 2 data models
│   ├── scorers/              # Scoring implementations
│   ├── pillars/              # Pillar implementations
│   └── utils/                # Utility modules
├── tests/                    # Test suite
├── docs/                     # Documentation
├── examples/                 # Example skills
└── scripts/                  # Utility scripts
```

## Testing Guidelines

### Unit Tests

```python
def test_static_scorer_frontmatter_valid():
    """ST-1: Valid frontmatter should earn full points."""
    skill_dir = Path("tests/fixtures/valid-skill")
    scorer = StaticScorer()
    result = scorer._st1_frontmatter(skill_dir)
    
    assert result.earned_points == 12
    assert result.passed is True
```

### Integration Tests

```python
def test_phase1_full_pipeline():
    """Phase 1 should complete in <1s with deterministic results."""
    skill_dir = Path("tests/fixtures/sample-skill")
    orchestrator = Phase1Orchestrator()
    
    result = orchestrator.evaluate(skill_dir)
    
    assert result.total_score > 0
    assert result.grade in (Grade.A, Grade.B, Grade.C, Grade.D, Grade.F)
    assert result.duration_seconds < 1.0
```

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create a git tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
4. Push tag: `git push origin v1.0.0`
5. GitHub Actions will build and publish to PyPI

## Getting Help

- **Documentation**: See [README.md](README.md) and [QUICK_START.md](QUICK_START.md)
- **Issues**: Check [GitHub Issues](https://github.com/skilleval/skilleval/issues)
- **Discussions**: Use [GitHub Discussions](https://github.com/skilleval/skilleval/discussions)
- **Email**: joinalahmed@gmail.com

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
