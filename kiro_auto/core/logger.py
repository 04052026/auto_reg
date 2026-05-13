"""Structured logging setup."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(config=None, name: str = "kiro_auto") -> logging.Logger:
    """Setup application logger with file + console output."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    level = getattr(config, "log_level", "INFO") if config else "INFO"
    log_file = getattr(config, "log_file", "logs/kiro-auto.log") if config else "logs/kiro-auto.log"

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler
    try:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)
    except Exception:
        pass

    return logger
