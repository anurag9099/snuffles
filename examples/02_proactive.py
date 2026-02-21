"""An agent that acts on its own every 30 seconds via a timer trigger."""

import asyncio
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, TimerTrigger


async def check_email(folder: str = "inbox") -> str:
    return "3 new emails: meeting at 3pm, PR review needed, lunch plans."


agent = Agent(
    name="assistant",
    instructions="You proactively check email and summarize what needs attention.",
    tools=[
        Tool(
            name="check_email",
            description="Check email inbox",
            parameters={
                "type": "object",
                "properties": {"folder": {"type": "string"}},
            },
            execute=check_email,
        )
    ],
)


async def main():
    bus = Bus()
    log = EventLog()
    orch = Orchestrator(bus, log)
    orch.add_agent(agent)
    orch.add_trigger(
        TimerTrigger(
            agent_name="assistant",
            interval_seconds=30,
            prompt="Check email and summarize anything important.",
        )
    )
    await orch.run()


asyncio.run(main())
