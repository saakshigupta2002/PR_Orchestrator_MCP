"""Logging wrapper for PR Orchestrator MCP."""

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with a default format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger
