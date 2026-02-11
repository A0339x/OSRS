"""Logging setup for the OSRS agent."""

import logging
import os
from datetime import datetime

from .config import LOGS_DIR


def setup_logger(name: str = "osrs_agent", level: int = logging.DEBUG) -> logging.Logger:
    """Create a logger that writes to both console and a dated log file."""
    os.makedirs(LOGS_DIR, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.handlers:
        return logger

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    console.setFormatter(console_fmt)
    logger.addHandler(console)

    # File handler — one file per day
    today = datetime.now().strftime("%Y-%m-%d")
    fh = logging.FileHandler(os.path.join(LOGS_DIR, f"{today}.log"))
    fh.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh.setFormatter(file_fmt)
    logger.addHandler(fh)

    return logger


log = setup_logger()
