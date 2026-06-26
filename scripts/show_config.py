#!/usr/bin/env python3
"""
Show current SkillEval configuration from .env and environment.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from skilleval.utils.env_config import load_env_config, print_config_summary, validate_config


def main():
    """Load and display configuration."""

    print("\nLoading configuration from .env and environment...")
    print()

    config = load_env_config()
    print_config_summary(config)

    # Validate configuration
    is_valid, error_msg = validate_config(config)

    print()
    if is_valid:
        print("✅ Configuration is valid and ready to use")
    else:
        print(f"❌ Configuration error: {error_msg}")
        print()
        print("Fix by:")
        print("  1. Copy .env.example to .env")
        print("  2. Edit .env and add your API key")
        print("  3. Run this script again to verify")
        return 1

    print()
    print("Ready to run evaluations:")
    print("  python3 -m skilleval.cli eval /path/to/skill")
    print("  ./batch_eval.sh /path/to/skills")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
