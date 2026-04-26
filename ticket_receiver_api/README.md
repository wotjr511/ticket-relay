# TicketReceiverAPI

TicketReceiverAPI is a lightweight FastAPI service that receives ticket JSON payloads, dispatches them to one of 12 type-specific handlers, and returns a success response after processing. It also exposes a health check endpoint for uptime checks and upstream relay systems.

## Project Structure

```text
ticket_receiver_api/
├── main.py
├── config.py
├── models.py
├── handlers.py
├── dispatcher.py
├── utils.py
├── requirements.txt
├── README.md
└── .env.example
```

## Installation

```bash
cd ticket_receiver_api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

## Configuration

Configuration is read from environment variables using `pydantic-settings`. Variables are prefixed with `TICKET_RECEIVER_`.

Copy the example file for local development:

```bash
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Available settings:

- `TICKET_RECEIVER_HOST`: Server bind host. Default: `0.0.0.0`
- `TICKET_RECEIVER_PORT`: Server bind port. Default: `8000`
- `TICKET_RECEIVER_LOG_LEVEL`: Logging level. Default: `INFO`
- `TICKET_RECEIVER_LOG_FILE`: File log path. Default: `ticket_receiver_api.log`
- `TICKET_RECEIVER_CORS_ORIGINS`: Comma-separated CORS origins. Default: `*`
- `TICKET_RECEIVER_RELOAD`: Enable Uvicorn reload for local development. Default: `false`

## Running

```bash
python main.py
```

Or run with Uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

API docs are available at:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Endpoints

### GET /health

Returns service health and a UTC timestamp.

```bash
curl http://localhost:8000/health
```

Example response:

```json
{
  "status": "healthy",
  "timestamp": "2026-04-25T14:00:00.000000Z"
}
```

### POST /tickets

Receives a flexible JSON ticket payload. The only required field is `type`, which can be an integer or an integer-like string from `1` through `12`.

```bash
curl -X POST http://localhost:8000/tickets ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": 3, \"title\": \"Sample Ticket\", \"data\": {\"source\": \"relay\"}}"
```

On macOS or Linux:

```bash
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{"type": 3, "title": "Sample Ticket", "data": {"source": "relay"}}'
```

Example response:

```json
{
  "status": "success",
  "message": "Ticket processed successfully",
  "type": 3,
  "ticket_id": "5ec78f63-d775-4d50-ad32-af44f84b40fa"
}
```

If `ticket_id` is not provided, the API generates one automatically. Extra fields are accepted and passed to the selected handler.

## Example Ticket Type Requests

Type `1`:

```bash
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"type\": 1, \"title\": \"Login issue\"}"
```

Type `6`:

```bash
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"type\": 6, \"title\": \"Billing update\", \"data\": {\"account_id\": \"A-100\"}}"
```

Type `12` as a string:

```bash
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"type\": \"12\", \"title\": \"Escalation\"}"
```

Unknown type:

```bash
curl -X POST http://localhost:8000/tickets -H "Content-Type: application/json" -d "{\"type\": 99, \"title\": \"Unknown\"}"
```

Returns HTTP `400 Bad Request`.

## Dispatcher Pattern

`dispatcher.py` contains a `TicketDispatcher` class with a dictionary mapping normalized ticket types to handler functions:

```python
{
    1: handle_type_1,
    2: handle_type_2,
    ...
    12: handle_type_12,
}
```

When `POST /tickets` receives a payload, the API:

1. Validates that a `type` field exists.
2. Converts integer-like strings such as `"3"` into integer type keys.
3. Looks up the corresponding handler in the dispatcher dictionary.
4. Calls the handler with the full ticket dictionary.
5. Returns a standard success response.

Each handler is defined in `handlers.py` as `handle_type_1()` through `handle_type_12()`. The handlers currently contain placeholder processing, log the ticket, and return a result dictionary. This keeps the structure production-ready while leaving clear extension points for real business logic.

## Logging

Logs are written to both stdout and the configured log file. The default format is:

```text
2026-04-25 14:00:00 | INFO     | main | TicketReceiverAPI starting
```

For long-running production deployments, configure log rotation with your process manager, container runtime, or platform logging system.

## Production Notes

- Run behind a reverse proxy or API gateway for TLS termination and request limits.
- Use explicit CORS origins instead of `*` when serving browser clients in production. Credentialed CORS requests are enabled only when origins are explicit.
- Run with a process manager such as systemd, Supervisor, Docker, Kubernetes, or a managed platform.
- Keep `TICKET_RECEIVER_RELOAD=false` in production.
- Add authentication before exposing the API publicly.
