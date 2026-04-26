"""FastAPI application entry point for TicketReceiverAPI."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from dispatcher import TicketDispatcher, UnknownTicketTypeError
from models import HealthResponse, TicketRequest, TicketResponse
from utils import setup_logging

settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)
dispatcher = TicketDispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and graceful shutdown events."""

    logger.info("TicketReceiverAPI starting")
    logger.info("Registered ticket handlers: %s", sorted(dispatcher.registered_types()))
    yield
    logger.info("TicketReceiverAPI shutting down")


app = FastAPI(
    title="TicketReceiverAPI",
    description="Receives ticket JSON payloads and dispatches them by type.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Convert unexpected exceptions into a safe JSON response."""

    logger.exception("Unhandled application error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    """Return API health status and current UTC timestamp."""

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
    )


@app.post("/tickets", response_model=TicketResponse, tags=["tickets"])
async def receive_ticket(ticket: TicketRequest) -> TicketResponse:
    """Receive a ticket payload, dispatch it by type, and return the result."""

    ticket_payload = ticket.to_payload()
    logger.info("Received ticket with type=%s", ticket.type)

    try:
        result = dispatcher.dispatch(ticket_payload)
    except UnknownTicketTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return TicketResponse(
        status="success",
        message="Ticket processed successfully",
        type=ticket.type,
        ticket_id=result["ticket_id"],
    )


def main() -> None:
    """Run the API server with Uvicorn."""

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.reload,
    )


if __name__ == "__main__":
    main()
