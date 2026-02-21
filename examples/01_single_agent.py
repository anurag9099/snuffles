"""One agent with one tool. The simplest possible setup."""

import asyncio
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, Message


async def web_search(query: str) -> str:
    return f"Results for '{query}': Tokyo has 13.96M people."


agent = Agent(
    name="assistant",
    instructions="You are a helpful assistant. Use web_search to find info.",
    tools=[
        Tool(
            name="web_search",
            description="Search the web",
            parameters={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            execute=web_search,
        )
    ],
)


async def main():
    bus = Bus()
    log = EventLog()
    orch = Orchestrator(bus, log)
    orch.add_agent(agent)
    await bus.send(
        Message(sender="user", to="assistant", content="What is Tokyo's population?")
    )
    await orch.run()


asyncio.run(main())
