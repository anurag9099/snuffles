"""Routes messages to agents. The simplest multi-agent coordinator.

We route by message.to field. Period.
"""

import asyncio

from snuffles.agent import Agent
from snuffles.bus import Bus
from snuffles.loop import run_loop
from snuffles.message import Message
from snuffles.log import EventLog


class Orchestrator:
    """Routes messages to agents by name."""

    def __init__(self, bus: Bus, event_log: EventLog):
        self.bus = bus
        self.event_log = event_log
        self.agents: dict[str, Agent] = {}
        self._triggers: list = []
        self._running = False
        self._run_task: asyncio.Task[None] | None = None

    def add_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def add_trigger(self, trigger) -> None:
        self._triggers.append(trigger)

    async def run(self) -> None:
        self._running = True
        self._run_task = asyncio.current_task()

        # Start triggers as background tasks
        trigger_tasks = [
            asyncio.create_task(t.start(self.bus)) for t in self._triggers
        ]

        try:
            while self._running:
                message = await self.bus.receive()

                self.event_log.record_event(
                    kind="message_routed",
                    data={
                        "from": message.sender,
                        "to": message.to,
                        "content": message.content[:200],
                    },
                )

                agent = self.agents.get(message.to)
                if agent is None:
                    await self.bus.reply(
                        Message(
                            sender="system",
                            to=message.sender,
                            content=f"No agent named '{message.to}'",
                        )
                    )
                    continue

                response = await run_loop(agent, message, self.event_log)

                if response:
                    await self.bus.reply(response)

                    # Re-inject any agent-to-agent reply through the same bus.
                    if response.to in self.agents and response.to != response.sender:
                        await self.bus.send(response)
        except asyncio.CancelledError:
            if self._running:
                raise

        finally:
            self._running = False
            self._run_task = None
            for t in self._triggers:
                t.stop()
            for task in trigger_tasks:
                task.cancel()
            if trigger_tasks:
                await asyncio.gather(*trigger_tasks, return_exceptions=True)

    def stop(self) -> None:
        self._running = False
        if self._run_task and not self._run_task.done():
            self._run_task.cancel()
