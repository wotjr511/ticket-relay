"""Ticket parsing and forwarding logic."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests
from requests import Session

from api_health_checker import ApiHealthChecker

LOGGER = logging.getLogger(__name__)


class TicketParseError(ValueError):
    """Raised when a ticket file cannot be parsed."""


class TicketForwarder:
    """Parse ticket files and forward them to a healthy API endpoint."""

    def __init__(
        self,
        target_url: str,
        timeout: float,
        max_retries: int,
        health_checker: ApiHealthChecker,
        session: Session | None = None,
    ) -> None:
        """Create a forwarder with retry behavior and health checking."""

        self.target_url = target_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.health_checker = health_checker
        self.session = session or requests.Session()

    def forward_file(self, path: Path) -> bool:
        """Parse a ticket file and forward it if the target API is healthy."""

        if not self.health_checker.is_healthy():
            LOGGER.warning("API is unhealthy; ticket will be retried later: %s", path)
            return False

        try:
            payload = self.parse_ticket(path)
        except TicketParseError as exc:
            LOGGER.error("Unable to parse ticket file %s: %s", path, exc)
            return True

        return self._post_with_retries(payload, path)

    def parse_ticket(self, path: Path) -> dict[str, Any]:
        """Parse a JSON ticket file into a dictionary payload."""

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except OSError as exc:
            raise TicketParseError(f"could not read file: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise TicketParseError(f"invalid JSON: {exc}") from exc

        if not isinstance(data, dict):
            raise TicketParseError("ticket JSON must be an object")
        if "ticket_id" not in data:
            raise TicketParseError("missing required field: ticket_id")
        if "subject" not in data:
            raise TicketParseError("missing required field: subject")

        return data

    def _post_with_retries(self, payload: dict[str, Any], source_path: Path) -> bool:
        """POST a parsed ticket payload with exponential backoff retries."""

        attempts = self.max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                response = self.session.post(
                    self.target_url,
                    json=payload,
                    timeout=self.timeout,
                )
                if 200 <= response.status_code < 300:
                    LOGGER.info("Forwarded ticket %s from %s", payload.get("ticket_id"), source_path)
                    return True

                LOGGER.warning(
                    "Forward attempt %s/%s failed for %s with status %s: %s",
                    attempt,
                    attempts,
                    source_path,
                    response.status_code,
                    response.text[:500],
                )
            except requests.RequestException as exc:
                LOGGER.warning(
                    "Forward attempt %s/%s failed for %s: %s",
                    attempt,
                    attempts,
                    source_path,
                    exc,
                )

            if attempt < attempts:
                time.sleep(min(2 ** (attempt - 1), 30))

        LOGGER.error("Exhausted retries for ticket file: %s", source_path)
        return False
