"""Utility functions for TicketReceiverAPI."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(log_level: str, log_file: Path) -> None:
    """Configure structured console and file logging."""

    log_path = log_file
    if not log_path.is_absolute():
        log_path = Path(__file__).resolve().parent / log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
