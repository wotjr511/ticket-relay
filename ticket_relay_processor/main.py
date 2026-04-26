"""Command-line entry point for TicketRelayProcessor."""

from __future__ import annotations

from config import get_config
from processor import run_forever
from utils import setup_logging


def main() -> None:
    """Start the TicketRelayProcessor application."""

    setup_logging()
    config = get_config()
    run_forever(config)


if __name__ == "__main__":
    main()
