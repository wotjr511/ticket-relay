"""Main orchestration for TicketRelayProcessor."""

from __future__ import annotations

import logging
import signal
import threading
import time
from pathlib import Path

from api_health_checker import ApiHealthChecker
from config import Config
from ticket_forwarder import TicketForwarder
from ticket_watcher import TicketWatcher

LOGGER = logging.getLogger(__name__)


class TicketRelayProcessor:
    """Continuously watch for ticket files and relay them to an API."""

    def __init__(self, config: Config) -> None:
        """Create the processor and its collaborator classes."""

        self.config = config
        self.shutdown_event = threading.Event()
        self.watcher = TicketWatcher(config.watch.directory)
        self.health_checker = ApiHealthChecker(
            health_check_url=config.api.health_check_url,
            timeout=config.api.timeout,
        )
        self.forwarder = TicketForwarder(
            target_url=config.api.target_url,
            timeout=config.api.timeout,
            max_retries=config.api.max_retries,
            health_checker=self.health_checker,
        )

    def install_signal_handlers(self) -> None:
        """Register SIGINT and SIGTERM handlers for graceful shutdown."""

        signal.signal(signal.SIGINT, self._handle_shutdown_signal)
        signal.signal(signal.SIGTERM, self._handle_shutdown_signal)

    def run(self) -> None:
        """Run the processing loop until shutdown is requested."""

        self.watcher.ensure_directory()
        LOGGER.info("Watching for tickets in %s", self.config.watch.directory)
        LOGGER.info("Forwarding healthy traffic to %s", self.config.api.target_url)

        while not self.shutdown_event.is_set():
            try:
                self.process_once()
            except Exception:
                LOGGER.exception("Unexpected error in processing loop")

            self.shutdown_event.wait(self.config.watch.poll_interval)

        LOGGER.info("TicketRelayProcessor stopped")

    def process_once(self) -> None:
        """Perform a single polling and forwarding cycle."""

        ticket_files = self.watcher.poll()
        for ticket_file in ticket_files:
            if self.shutdown_event.is_set():
                break
            self._process_ticket(ticket_file)

    def stop(self) -> None:
        """Request processor shutdown."""

        self.shutdown_event.set()

    def _process_ticket(self, ticket_file: Path) -> None:
        """Forward a single ticket file and mark it for retry when needed."""

        LOGGER.info("Discovered ticket file: %s", ticket_file)
        success = self.forwarder.forward_file(ticket_file)
        if not success:
            self.watcher.mark_unprocessed(ticket_file)

    def _handle_shutdown_signal(self, signum: int, _frame: object) -> None:
        """Handle process signals by requesting a graceful shutdown."""

        LOGGER.info("Received signal %s; shutting down", signum)
        self.stop()


def run_forever(config: Config) -> None:
    """Create and run a TicketRelayProcessor."""

    processor = TicketRelayProcessor(config)
    processor.install_signal_handlers()
    processor.run()
