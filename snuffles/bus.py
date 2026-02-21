"""The central nervous system. All communication flows through here.

Two async queues + subscriber list for observability.
"""

import asyncio

from snuffles.message import Message


class Bus:
    """The central nervous system. All communication flows through here."""

    def __init__(self):
        self._inbound: asyncio.Queue[Message] = asyncio.Queue()
        self._outbound: asyncio.Queue[Message] = asyncio.Queue()
        self._subscribers: list[asyncio.Queue[Message]] = []

    async def send(self, message: Message) -> None:
        """Send a message to be processed by an agent."""
        await self._inbound.put(message)

    async def receive(self) -> Message:
        """Wait for next inbound message. Called by orchestrator."""
        return await self._inbound.get()

    async def reply(self, message: Message) -> None:
        """Agent publishes an outbound message."""
        await self._outbound.put(message)
        for sub in self._subscribers:
            await sub.put(message)

    async def next_reply(self) -> Message:
        """Wait for next outbound message. Called by channels/UI."""
        return await self._outbound.get()

    def subscribe(self) -> asyncio.Queue[Message]:
        """Subscribe to ALL outbound messages (for logging, UI, etc.)."""
        q: asyncio.Queue[Message] = asyncio.Queue()
        self._subscribers.append(q)
        return q
