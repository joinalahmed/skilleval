# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-06-25

### Added
- Initial public release
- Phase 1: Packaging & Security (0-100 points)
  - Static Tests: ST-1 through ST-8 (50 points)
  - Security: Layer 1 built-in checks (50 points)
- Phase 2: Runtime Effectiveness (0-100 points)
  - Functional Correctness: Baseline comparison (50 points)
  - LLM Safety: Deterministic trace analysis (50 points)
- Dual-score reporting with A-F grading
- Confidence-weighted security findings
- OWASP coverage: Web (2021), API (2023), LLM (2023), Agentic (2026)
- 82+ security patterns
- 6 deterministic grader types
- Container isolation with Podman
- CLI with JSON/text output formats
- Comprehensive documentation

### Security
- 18 Layer 1 security checks (zero dependencies)
- Hardcoded secret detection (10+ patterns)
- Code injection detection (SQL, XSS, Command)
- Prompt injection detection
- CVE scanning integration (pip-audit, grype)

### Performance
- Phase 1: <1 second per skill
- 100% deterministic (no LLM-as-judge)
- Batch processing: 200+ skills/second

### Documentation
- README.md with quick start
- QUICK_START.md (5-minute guide)
- SETUP_GUIDE.md (installation instructions)
- Architecture documentation
- Contributing guidelines
- MIT License

[Unreleased]: https://github.com/skilleval/skilleval/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/skilleval/skilleval/releases/tag/v1.0.0
