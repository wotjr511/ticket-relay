# TicketRelayProcessor

TicketRelayProcessor is a lightweight Python 3.9+ process that watches a directory for ticket files, checks API health, and forwards parsed ticket data only when the target API is healthy.

## Project Structure

```text
ticket_relay_processor/
├── config.ini
├── main.py
├── config.py
├── ticket_watcher.py
├── api_health_checker.py
├── ticket_forwarder.py
├── processor.py
├── utils.py
├── requirements.txt
└── README.md
```

## Installation

```bash
cd ticket_relay_processor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, activate the virtual environment with:

```bash
source .venv/bin/activate
```

## Configuration

All runtime settings live in `config.ini`:

```ini
[watch]
directory = ./tickets
poll_interval = 5

[api]
target_url = https://api.example.com/tickets
health_check_url = https://api.example.com/health
timeout = 10
max_retries = 3
```

Settings:

- `watch.directory`: Directory to monitor for new ticket files. Relative paths are resolved from the project directory.
- `watch.poll_interval`: Number of seconds between directory scans.
- `api.target_url`: API endpoint that receives ticket payloads.
- `api.health_check_url`: API endpoint used to verify target health before forwarding.
- `api.timeout`: Request timeout in seconds.
- `api.max_retries`: Number of retry attempts after the initial forwarding attempt fails.

You can update settings programmatically with:

```python
from config import set_config

set_config("watch", "poll_interval", "10")
set_config("api", "target_url", "https://api.example.com/tickets")
```

`set_config` writes the updated INI file safely and reloads the active configuration.

## Running

```bash
python main.py
```

The process writes logs to both the console and `ticket_relay_processor.log`.

Stop the processor with `Ctrl+C` or by sending `SIGTERM`. The shutdown handler lets the current loop finish cleanly.

## Sample Ticket File

Create a JSON file in the configured ticket directory, for example `tickets/ticket-1001.json`:

```json
{
  "ticket_id": "TCK-1001",
  "subject": "Unable to access account",
  "description": "Customer cannot sign in after password reset.",
  "priority": "high",
  "requester": {
    "name": "Jane Doe",
    "email": "jane@example.com"
  },
  "created_at": "2026-04-25T09:00:00Z"
}
```

Required fields:

- `ticket_id`
- `subject`

Additional fields are preserved and forwarded as part of the JSON payload.

## Processing Behavior

1. The watcher scans the configured directory at the configured interval.
2. Files are considered only after their size is stable across a short check.
3. Before each forward attempt, the health endpoint must return an HTTP 2xx response.
4. Valid ticket JSON is posted to `api.target_url`.
5. Failed API sends are retried with exponential backoff.
6. Tickets that could not be sent because the API is unhealthy or forwarding failed are made eligible for a later retry.
7. Malformed tickets are logged as errors and are not retried indefinitely.

## Production Notes

- Run the processor under a service manager such as systemd, Windows Services, Supervisor, or a container orchestrator.
- Point `watch.directory` to durable storage if ticket files must survive restarts.
- Ensure the configured API endpoints use HTTPS in production.
- Configure log rotation externally if this process runs long term.
- Consider archiving or deleting successfully processed files according to your operational policy. This implementation leaves source files in place and tracks processed files in memory for the life of the process.
