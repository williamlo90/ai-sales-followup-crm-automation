# Local readiness alerts

`scripts/readiness_monitor.py` checks the actual readiness endpoint once and records state transitions in a local SQLite outbox. A healthy initial check is quiet. An unavailable service creates an alert; recovery creates a separate event. Repeated unchanged checks do not create new events. HTTP failures and non-2xx receiver responses leave events pending across monitor restarts.

Example from the project directory, after configuring a local receiver:

```powershell
.venv/Scripts/python.exe -m scripts.readiness_monitor --state local/readiness.sqlite --health http://127.0.0.1:8044/health/ready --receiver http://127.0.0.1:8056/events
```

The state directory must already exist. URLs must be explicit loopback HTTP addresses without credentials or query strings. The monitor sends only event ID, service URL, state and observed timestamp; it never includes health-response bodies, customer records or credentials. Redirects and environment proxies are disabled. The receiver should persist and deduplicate `event_id` / `Idempotency-Key` before acknowledging. Delivery is at-least-once: a crash after receiver acceptance and before the local acknowledgement can cause a repeat with the same ID.

Run the command from the selected deployment scheduler; no recurring task is installed automatically. Use a distinct state file for each receiver configuration and preserve it during upgrades. Pending events are retried in order at the next invocation. This implementation monitors API readiness only; workflow backlog/unknown-outcome monitoring and a human-facing notification channel remain separate operational work.

`scripts/readiness_alert_drill.py` observes the real lab API becoming unavailable at the end of an owned test session. Its temporary local HTTP receiver first rejects an event with503, then accepts the same durable event ID. This is a controlled local delivery drill, not evidence of email/Slack delivery, human acknowledgement, host reboot or a continuously deployed monitor.
