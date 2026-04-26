"""Structured ticket processing history logging."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, Mapping, Optional


class TicketLogger:
    """Write structured processing results for individual tickets.

    The logger writes one JSON object per line to ``logs/ticket_processing.log``
    and rotates the file daily. Rotated files are named with the date that
    completed, for example ``ticket_processing_2026-04-26.log``.

    Python's logging handlers are thread-safe, so callers can share a single
    ``TicketLogger`` instance across worker threads.
    """

    LOGGER_NAME = "ticket_processing_history"

    def __init__(
        self,
        log_dir: Path,
        log_level: str = "INFO",
        console_output: bool = True,
    ) -> None:
        """Create a ticket processing logger.

        Args:
            log_dir: Directory that will contain ``ticket_processing.log``.
            log_level: Standard logging level name, such as ``INFO`` or
                ``DEBUG``.
            console_output: When True, also emit success/failure summaries to
                stdout.
        """

        self.log_dir = log_dir.resolve()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / "ticket_processing.log"
        self.logger = logging.getLogger(self.LOGGER_NAME)
        self.logger.setLevel(self._parse_log_level(log_level))
        self.logger.propagate = False
        self._configure_handlers(console_output)

    def log_processing_result(
        self,
        *,
        ticket_id: Optional[str],
        filename: str,
        start_time: datetime,
        end_time: datetime,
        success: bool,
        api_status_code: Optional[int],
        api_message: Optional[str],
        error_message: Optional[str],
        ticket_content: Optional[Mapping[str, Any]] = None,
    ) -> None:
        """Record the processing result for one ticket.

        Args:
            ticket_id: Ticket identifier from the payload when available.
            filename: Source ticket file name or path.
            start_time: Processing start timestamp.
            end_time: Processing completion timestamp.
            success: True when the ticket was forwarded successfully.
            api_status_code: HTTP status code returned by the target API.
            api_message: Response text or concise API response message.
            error_message: Error details when processing failed.
            ticket_content: Optional parsed ticket payload used to create a
                compact content summary.
        """

        duration_seconds = max((end_time - start_time).total_seconds(), 0.0)
        entry = {
            "ticket_id": ticket_id or filename,
            "filename": filename,
            "processing_start_time": self._to_iso8601(start_time),
            "processing_end_time": self._to_iso8601(end_time),
            "success": success,
            "status": "success" if success else "failure",
            "target_api": {
                "status_code": api_status_code,
                "message": self._truncate(api_message),
            },
            "error_message": self._truncate(error_message),
            "processing_duration_seconds": round(duration_seconds, 6),
            "ticket_content_summary": self._summarize_ticket(ticket_content),
        }

        message = json.dumps(entry, ensure_ascii=False, sort_keys=True)
        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)

    def _configure_handlers(self, console_output: bool) -> None:
        """Configure file and optional console handlers once."""

        formatter = logging.Formatter("%(message)s")
        self.logger.handlers.clear()

        file_handler = TimedRotatingFileHandler(
            filename=self.log_path,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
            utc=False,
        )
        file_handler.suffix = "%Y-%m-%d.log"
        file_handler.namer = self._rotation_namer
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(logging.INFO)
            self.logger.addHandler(console_handler)

    def _rotation_namer(self, default_name: str) -> str:
        """Convert ``ticket_processing.log.YYYY-MM-DD.log`` to requested name."""

        path = Path(default_name)
        marker = ".log."
        if marker not in path.name:
            return default_name
        stem, date_suffix = path.name.split(marker, 1)
        return str(path.with_name(f"{stem}_{date_suffix}"))

    def _parse_log_level(self, log_level: str) -> int:
        """Return a logging level from a string level name."""

        level = getattr(logging, log_level.upper(), logging.INFO)
        if not isinstance(level, int):
            return logging.INFO
        return level

    def _to_iso8601(self, value: datetime) -> str:
        """Return an ISO 8601 timestamp with timezone information."""

        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def _summarize_ticket(
        self,
        ticket_content: Optional[Mapping[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Build a compact, structured summary of the ticket payload."""

        if ticket_content is None:
            return None

        summary_keys = ("ticket_id", "subject", "priority", "status", "created_at")
        summary = {
            key: self._truncate(ticket_content.get(key))
            for key in summary_keys
            if key in ticket_content
        }
        summary["field_count"] = len(ticket_content)
        return summary

    def _truncate(self, value: Optional[Any], max_length: int = 500) -> Optional[str]:
        """Return a bounded string representation for log-friendly fields."""

        if value is None:
            return None
        text = str(value)
        if len(text) <= max_length:
            return text
        return f"{text[:max_length]}..."
