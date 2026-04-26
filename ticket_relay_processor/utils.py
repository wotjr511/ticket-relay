"""Shared utilities for TicketRelayProcessor."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(log_file: Path | str = "ticket_relay_processor.log") -> None:
    """Configure console and file logging for the processor."""

    log_path = Path(log_file)
    if not log_path.is_absolute():
        log_path = Path(__file__).resolve().parent / log_path

    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def is_file_stable(path: Path, wait_seconds: float = 0.25) -> bool:
    """Return True when file size appears stable across a short interval."""

    import time

    try:
        first_size = path.stat().st_size
        time.sleep(wait_seconds)
        second_size = path.stat().st_size
    except OSError:
        return False
    return first_size == second_size
