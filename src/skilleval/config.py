"""
Configuration management for SkillEval.
"""

from pathlib import Path
from typing import Optional

import yaml

from skilleval.models import Config


def load_config(config_path: Optional[Path] = None) -> Config:
    """
    Load configuration from file or use defaults.

    Priority:
    1. Explicitly provided config_path
    2. ~/.skilleval/config.yaml
    3. ./skilleval.yaml
    4. Defaults
    """
    # Try explicit path first
    if config_path and config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f)
        return Config(**data)

    # Try user config
    user_config = Path.home() / ".skilleval" / "config.yaml"
    if user_config.exists():
        with open(user_config) as f:
            data = yaml.safe_load(f)
        return Config(**data)

    # Try local config
    local_config = Path("skilleval.yaml")
    if local_config.exists():
        with open(local_config) as f:
            data = yaml.safe_load(f)
        return Config(**data)

    # Use defaults
    return Config()


def create_default_config(output_path: Path):
    """Create a default configuration file."""

    default_config = """# SkillEval Configuration

framework_version: "0.1.0"
deterministic: true

static_tests:
  strict_mode: true
  check_description_steps: true
  min_description_length: 30
  min_body_length: 100

security:
  min_score: 60
  fail_on_critical: true
  fail_on_high: false
  approved_registries:
    - docker.io
    - docker.io
    - quay.io
  approved_licenses:
    - MIT
    - Apache-2.0
    - BSD-3-Clause
    - GPL-3.0
    - LGPL-2.1
    - MPL-2.0

harness:
  container_runtime: podman
  base_image: docker.io/alpine:latest
  selinux_enforcing: true
  network_isolated: true
  timeout_seconds: 300
  max_turns: 50
  max_tokens: 50000

scoring:
  weights:
    static_tests: 0.20
    security: 0.30
    harness: 0.50
  thresholds:
    approve: 75
    conditional: 60
    reject: 60

output_format: json  # json | html | both
output_directory: ./reports

logging_level: INFO  # DEBUG | INFO | WARNING | ERROR
logging_format: pretty  # pretty | json
"""

    with open(output_path, "w") as f:
        f.write(default_config)
