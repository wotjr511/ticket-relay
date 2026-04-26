"""Ticket parsing and forwarding logic."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests
from requests import Session

from api_health_checker import ApiHealthChecker

LOGGER = logging.getLogger(__name__)


class TicketParseError(ValueError):
    """Raised when a ticket file cannot be parsed."""


@dataclass(frozen=True)
class TicketForwardResult:
    """Detailed result for one ticket forwarding attempt."""

    filename: str
    start_time: datetime
    end_time: datetime
    success: bool
    should_retry: bool
    ticket_id: Optional[str] = None
    api_status_code: Optional[int] = None
    api_message: Optional[str] = None
    error_message: Optional[str] = None
    ticket_content: Optional[dict[str, Any]] = None


class TicketForwarder:
    """Parse ticket files and forward them to a healthy API endpoint."""

    def __init__(
        self,
        target_url: str,
        timeout: float,
        max_retries: int,
        health_checker: ApiHealthChecker,
        session: Optional[Session] = None,
    ) -> None:
        """Create a forwarder with retry behavior and health checking."""

        self.target_url = target_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.health_checker = health_checker
        self.session = session or requests.Session()

    def forward_file(self, path: Path) -> TicketForwardResult:
        """Parse a ticket file and forward it if the target API is healthy."""

        start_time = datetime.now(timezone.utc)

        if not self.health_checker.is_healthy():
            LOGGER.warning("API is unhealthy; ticket will be retried later: %s", path)
            return self._build_result(
                path=path,
                start_time=start_time,
                success=False,
                should_retry=True,
                error_message="API health check failed",
            )

        try:
            payload = self.parse_ticket(path)
        except TicketParseError as exc:
            LOGGER.error("Unable to parse ticket file %s: %s", path, exc)
            return self._build_result(
                path=path,
                start_time=start_time,
                success=False,
                should_retry=False,
                error_message=str(exc),
            )

        return self._post_with_retries(payload, path, start_time)

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

    def _post_with_retries(
        self,
        payload: dict[str, Any],
        source_path: Path,
        start_time: datetime,
    ) -> TicketForwardResult:
        """POST a parsed ticket payload with exponential backoff retries."""

        attempts = self.max_retries + 1
        last_status_code: Optional[int] = None
        last_api_message: Optional[str] = None
        last_error_message: Optional[str] = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.session.post(
                    self.target_url,
                    json=payload,
                    timeout=self.timeout,
                )
                last_status_code = response.status_code
                last_api_message = response.text[:500]
                if 200 <= response.status_code < 300:
                    LOGGER.info("Forwarded ticket %s from %s", payload.get("ticket_id"), source_path)
                    return self._build_result(
                        path=source_path,
                        start_time=start_time,
                        success=True,
                        should_retry=False,
                        payload=payload,
                        api_status_code=response.status_code,
                        api_message=response.text[:500],
                    )

                LOGGER.warning(
                    "Forward attempt %s/%s failed for %s with status %s: %s",
                    attempt,
                    attempts,
                    source_path,
                    response.status_code,
                    response.text[:500],
                )
                last_error_message = f"Target API returned status {response.status_code}"
            except requests.RequestException as exc:
                last_error_message = str(exc)
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
        return self._build_result(
            path=source_path,
            start_time=start_time,
            success=False,
            should_retry=True,
            payload=payload,
            api_status_code=last_status_code,
            api_message=last_api_message,
            error_message=last_error_message or "Exhausted retries",
        )

    def _build_result(
        self,
        *,
        path: Path,
        start_time: datetime,
        success: bool,
        should_retry: bool,
        payload: Optional[dict[str, Any]] = None,
        api_status_code: Optional[int] = None,
        api_message: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> TicketForwardResult:
        """Create a structured forwarding result with completion timing."""

        ticket_id = payload.get("ticket_id") if payload else None
        return TicketForwardResult(
            filename=str(path),
            start_time=start_time,
            end_time=datetime.now(timezone.utc),
            success=success,
            should_retry=should_retry,
            ticket_id=str(ticket_id) if ticket_id is not None else None,
            api_status_code=api_status_code,
            api_message=api_message,
            error_message=error_message,
            ticket_content=payload,
        )
