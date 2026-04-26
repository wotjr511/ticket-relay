"""API health checking for TicketRelayProcessor."""

from __future__ import annotations

import logging

import requests
from requests import Session

LOGGER = logging.getLogger(__name__)


class ApiHealthChecker:
    """Perform health checks against the configured API endpoint."""

    def __init__(self, health_check_url: str, timeout: float, session: Session | None = None) -> None:
        """Create a health checker for a URL."""

        self.health_check_url = health_check_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def is_healthy(self) -> bool:
        """Return True when the health endpoint responds with a 2xx status."""

        try:
            response = self.session.get(self.health_check_url, timeout=self.timeout)
            if 200 <= response.status_code < 300:
                LOGGER.debug("Health check succeeded with status %s", response.status_code)
                return True

            LOGGER.warning(
                "Health check failed for %s with status %s",
                self.health_check_url,
                response.status_code,
            )
            return False
        except requests.RequestException as exc:
            LOGGER.warning("Health check request failed for %s: %s", self.health_check_url, exc)
            return False
