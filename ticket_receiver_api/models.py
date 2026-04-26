"""Pydantic models for TicketReceiverAPI."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

TicketType = Union[int, str]


class TicketRequest(BaseModel):
    """Flexible incoming ticket payload that requires a type field."""

    type: TicketType = Field(..., description="Ticket type used by the dispatcher.")

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def validate_type(self) -> "TicketRequest":
        """Ensure ticket type is not an empty string."""

        if isinstance(self.type, str) and not self.type.strip():
            raise ValueError("type cannot be empty")
        return self

    def to_payload(self) -> dict[str, Any]:
        """Return the complete ticket payload, including extra fields."""

        payload = self.model_dump()
        payload.setdefault("ticket_id", str(uuid4()))
        return payload


class TicketResponse(BaseModel):
    """Response returned after successful ticket processing."""

    status: str
    message: str
    type: TicketType
    ticket_id: str


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    timestamp: datetime
