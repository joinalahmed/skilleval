"""
Logging utilities for SkillEval.
"""

import logging
import sys
from typing import Optional


# Global logger instance
logger = logging.getLogger("skilleval")


def setup_logging(level: str = "INFO", format_style: str = "pretty"):
    """
    Setup logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        format_style: Format style ('pretty' or 'json')
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure logger
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    # Set format based on style
    if format_style == "json":
        formatter = logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}'
        )
    else:  # pretty
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Don't propagate to root logger
    logger.propagate = False
