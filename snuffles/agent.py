"""An agent is: identity + instructions + tools. Nothing more."""

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable


@dataclass
class Tool:
    """A function the agent can call."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    execute: Callable[..., Awaitable[str]]  # The actual function


@dataclass
class Agent:
    """An agent is: identity + instructions + tools.

    This is the full definition. No base classes, no mixins,
    no registration, and no lifecycle hooks.
    """

    name: str
    instructions: str
    tools: list[Tool] = field(default_factory=list)
    model: str = field(
        default_factory=lambda: os.environ.get("LLM_MODEL", "gpt-4.1-mini")
    )
    max_iterations: int = 10

    def tool_schemas(self) -> list[dict]:
        """Return tool definitions in OpenAI function-calling format."""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools
        ]

    def get_tool(self, name: str) -> Tool | None:
        return next((t for t in self.tools if t.name == name), None)
