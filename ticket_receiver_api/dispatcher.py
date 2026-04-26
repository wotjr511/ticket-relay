"""Dictionary-based dispatcher for routing tickets by type."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Union

from handlers import (
    handle_type_1,
    handle_type_10,
    handle_type_11,
    handle_type_12,
    handle_type_2,
    handle_type_3,
    handle_type_4,
    handle_type_5,
    handle_type_6,
    handle_type_7,
    handle_type_8,
    handle_type_9,
)

TicketType = Union[int, str]
TicketHandler = Callable[[dict[str, Any]], dict[str, Any]]


class UnknownTicketTypeError(ValueError):
    """Raised when no handler exists for a ticket type."""


class TicketDispatcher:
    """Dispatch ticket dictionaries to type-specific handlers."""

    def __init__(self) -> None:
        """Initialize the dictionary-based handler registry."""

        self._handlers: dict[int, TicketHandler] = {
            1: handle_type_1,
            2: handle_type_2,
            3: handle_type_3,
            4: handle_type_4,
            5: handle_type_5,
            6: handle_type_6,
            7: handle_type_7,
            8: handle_type_8,
            9: handle_type_9,
            10: handle_type_10,
            11: handle_type_11,
            12: handle_type_12,
        }

    def dispatch(self, ticket: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a ticket to the handler matching its type."""

        normalized_type = self._normalize_type(ticket.get("type"))
        handler = self._handlers.get(normalized_type)
        if handler is None:
            raise UnknownTicketTypeError(
                f"Unknown ticket type: {ticket.get('type')}. Supported types: {self.registered_types()}"
            )
        return handler(ticket)

    def registered_types(self) -> list[int]:
        """Return the currently registered ticket types."""

        return sorted(self._handlers.keys())

    def _normalize_type(self, ticket_type: object) -> int:
        """Normalize integer-like ticket types to an integer key."""

        if isinstance(ticket_type, bool):
            raise UnknownTicketTypeError("Ticket type must be an integer from 1 to 12")
        if isinstance(ticket_type, int):
            return ticket_type
        if isinstance(ticket_type, str):
            stripped = ticket_type.strip()
            if stripped.isdigit():
                return int(stripped)
        raise UnknownTicketTypeError("Ticket type must be an integer or integer-like string from 1 to 12")
