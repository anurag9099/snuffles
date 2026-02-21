"""Timer and FileWatch triggers. Proactive = timer-injected messages."""

import asyncio
from pathlib import Path
from dataclasses import dataclass

from snuffles.message import Message
from snuffles.bus import Bus


@dataclass
class TimerTrigger:
    """Periodically wakes an agent. The HEARTBEAT pattern.

    A proactive agent is just an agent that receives messages
    from a timer instead of a human.
    """

    agent_name: str
    interval_seconds: float
    prompt: str = "Check if there is anything that needs your attention."
    _running: bool = False

    async def start(self, bus: Bus) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(self.interval_seconds)
            if self._running:
                await bus.send(
                    Message(
                        sender="timer",
                        to=self.agent_name,
                        content=self.prompt,
                    )
                )

    def stop(self) -> None:
        self._running = False


@dataclass
class FileWatchTrigger:
    """Wakes an agent when a file changes."""

    agent_name: str
    watch_path: Path
    poll_seconds: float = 10.0
    _running: bool = False
    _last_mtime: float = 0.0

    async def start(self, bus: Bus) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(self.poll_seconds)
            if self._running and self.watch_path.exists():
                mtime = self.watch_path.stat().st_mtime
                if mtime > self._last_mtime:
                    self._last_mtime = mtime
                    content = self.watch_path.read_text()
                    await bus.send(
                        Message(
                            sender="file_watch",
                            to=self.agent_name,
                            content=f"File changed: {self.watch_path}\n\nContents:\n{content}",
                        )
                    )

    def stop(self) -> None:
        self._running = False
