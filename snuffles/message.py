"""The atom of communication between agents and the outside world."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    """The atom of communication between agents and the outside world."""

    sender: str  # Who sent it (agent name, "user", "timer", "file_watch")
    to: str  # Who it's for (agent name, "user")
    content: str  # The actual content
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Event:
    """A record of something that happened. Append-only.

    Event kinds:
      message_routed   - A message was sent to an agent
      loop_start       - An agent started processing
      llm_call         - Agent called the LLM
      llm_response     - LLM returned text (no tool calls)
      tool_call        - Agent is executing a tool
      tool_result      - Tool returned a result
      loop_end         - Agent finished processing
      loop_max_iters   - Agent hit iteration limit
      trigger_fired    - A timer/file trigger activated
    """

    kind: str
    agent: str = ""
    data: dict = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
