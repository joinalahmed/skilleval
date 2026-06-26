"""
Environment configuration loader with .env file support.

Loads configuration from .env file and environment variables.
"""

import os
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


@dataclass
class EnvConfig:
    """Environment configuration for SkillEval."""

    # Provider settings
    llm_provider: Literal["google", "anthropic"] = "google"

    # API keys
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Model settings
    google_model: str = "gemini-2.0-flash-exp"
    anthropic_model: str = "claude-sonnet-4-20250514"

    # Agent settings
    max_tokens: int = 8192
    max_turns: int = 25
    timeout_seconds: int = 300
    temperature: float = 1.0

    # Cost tracking
    enable_cost_tracking: bool = True
    cost_warning_threshold: float = 0.10


def load_env_config(env_file: Optional[Path] = None) -> EnvConfig:
    """
    Load configuration from .env file and environment variables.

    Args:
        env_file: Optional path to .env file. If not provided, searches for
                  .env in current directory and parent directories.

    Returns:
        EnvConfig with loaded settings
    """

    # Load .env file if available
    if DOTENV_AVAILABLE:
        if env_file and env_file.exists():
            load_dotenv(env_file)
        else:
            # Search for .env in current and parent directories
            current_dir = Path.cwd()
            for parent in [current_dir] + list(current_dir.parents):
                env_path = parent / ".env"
                if env_path.exists():
                    load_dotenv(env_path)
                    break

    # Load configuration from environment variables
    config = EnvConfig()

    # Provider selection
    provider = os.getenv("LLM_PROVIDER", "google").lower()
    if provider in ["google", "anthropic"]:
        config.llm_provider = provider

    # API keys
    config.google_api_key = os.getenv("GOOGLE_API_KEY")
    config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

    # Model settings
    config.google_model = os.getenv("GOOGLE_MODEL", "gemini-2.0-flash-exp")
    config.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

    # Agent settings
    try:
        config.max_tokens = int(os.getenv("MAX_TOKENS", "8192"))
    except ValueError:
        config.max_tokens = 8192

    try:
        config.max_turns = int(os.getenv("MAX_TURNS", "25"))
    except ValueError:
        config.max_turns = 25

    try:
        config.timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "300"))
    except ValueError:
        config.timeout_seconds = 300

    try:
        config.temperature = float(os.getenv("TEMPERATURE", "1.0"))
    except ValueError:
        config.temperature = 1.0

    # Cost tracking
    config.enable_cost_tracking = os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true"

    try:
        config.cost_warning_threshold = float(os.getenv("COST_WARNING_THRESHOLD", "0.10"))
    except ValueError:
        config.cost_warning_threshold = 0.10

    return config


def get_active_provider(config: EnvConfig) -> str:
    """
    Determine which provider to use based on configuration.

    Args:
        config: Environment configuration

    Returns:
        Active provider name ('google' or 'anthropic')
    """

    # If provider explicitly set and has key, use it
    if config.llm_provider == "google" and config.google_api_key:
        return "google"
    elif config.llm_provider == "anthropic" and config.anthropic_api_key:
        return "anthropic"

    # Auto-detect based on available keys
    if config.google_api_key:
        return "google"
    elif config.anthropic_api_key:
        return "anthropic"

    # Default to google (will fail if no key)
    return "google"


def get_model_for_provider(config: EnvConfig, provider: str) -> str:
    """
    Get model name for given provider.

    Args:
        config: Environment configuration
        provider: Provider name ('google' or 'anthropic')

    Returns:
        Model name
    """

    if provider == "google":
        return config.google_model
    elif provider == "anthropic":
        return config.anthropic_model
    else:
        return "gemini-2.0-flash-exp"


def get_api_key_for_provider(config: EnvConfig, provider: str) -> Optional[str]:
    """
    Get API key for given provider.

    Args:
        config: Environment configuration
        provider: Provider name ('google' or 'anthropic')

    Returns:
        API key or None
    """

    if provider == "google":
        return config.google_api_key
    elif provider == "anthropic":
        return config.anthropic_api_key
    else:
        return None


def print_config_summary(config: EnvConfig) -> None:
    """
    Print configuration summary for debugging.

    Args:
        config: Environment configuration
    """

    provider = get_active_provider(config)
    model = get_model_for_provider(config, provider)

    print("=" * 70)
    print("SkillEval Configuration")
    print("=" * 70)
    print(f"Provider: {provider}")
    print(f"Model: {model}")
    print(f"Max Tokens: {config.max_tokens}")
    print(f"Max Turns: {config.max_turns}")
    print(f"Temperature: {config.temperature}")
    print(f"Timeout: {config.timeout_seconds}s")

    # API key status (hide actual keys)
    if config.google_api_key:
        print(f"Google API Key: Set ({config.google_api_key[:10]}...)")
    else:
        print("Google API Key: Not set")

    if config.anthropic_api_key:
        print(f"Anthropic API Key: Set ({config.anthropic_api_key[:10]}...)")
    else:
        print("Anthropic API Key: Not set")

    print(f"Cost Tracking: {'Enabled' if config.enable_cost_tracking else 'Disabled'}")
    print(f"Cost Warning Threshold: ${config.cost_warning_threshold}")
    print("=" * 70)


def validate_config(config: EnvConfig) -> tuple[bool, str]:
    """
    Validate configuration.

    Args:
        config: Environment configuration

    Returns:
        Tuple of (is_valid, error_message)
    """

    provider = get_active_provider(config)
    api_key = get_api_key_for_provider(config, provider)

    if not api_key:
        return False, f"No API key found for provider '{provider}'. Set {provider.upper()}_API_KEY in .env or environment."

    if config.max_tokens < 1024:
        return False, f"MAX_TOKENS ({config.max_tokens}) too low. Must be >= 1024."

    if config.max_turns < 1:
        return False, f"MAX_TURNS ({config.max_turns}) too low. Must be >= 1."

    if config.temperature < 0 or config.temperature > 2:
        return False, f"TEMPERATURE ({config.temperature}) out of range. Must be 0.0-2.0."

    return True, ""
