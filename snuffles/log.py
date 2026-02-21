"""Append-only JSONL event log. The ENTIRE observability story.

No metrics server, no tracing framework. A file you can read with
cat, grep, and jq.
"""

import json
from pathlib import Path

from snuffles.message import Event


class EventLog:
    """Append-only JSONL event log."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[Event] = []

    def record(self, event: Event) -> None:
        self.events.append(event)

        # Print to stdout (real-time visibility)
        ts = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        print(f"[{ts}] {event.kind:20s} | {event.agent:12s} | {_fmt(event.data)}")

        # Append to JSONL file
        if self.path:
            line = json.dumps(
                {
                    "ts": event.timestamp.isoformat(),
                    "kind": event.kind,
                    "agent": event.agent,
                    "data": event.data,
                },
                ensure_ascii=False,
            )
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")

    def record_event(self, kind: str, agent: str = "", data: dict = None) -> None:
        self.record(Event(kind=kind, agent=agent, data=data or {}))


def _fmt(data: dict) -> str:
    parts = []
    for k, v in data.items():
        s = str(v)
        if len(s) > 80:
            s = s[:77] + "..."
        parts.append(f"{k}={s}")
    return ", ".join(parts)
