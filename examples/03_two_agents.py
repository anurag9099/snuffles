"""Two agents that collaborate: a researcher and a writer."""

import asyncio
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, Message


async def web_search(query: str) -> str:
    return f"Results for '{query}': Tokyo GDP is $1.9T, population 13.96M..."


async def write_document(title: str, content: str) -> str:
    return f"Document '{title}' saved ({len(content)} chars)."


researcher = Agent(
    name="researcher",
    instructions="""You research topics using web_search.
    When done, send your findings to the 'writer' agent.""",
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

writer = Agent(
    name="writer",
    instructions="""You write documents from research findings.
    Use write_document to save the final output.""",
    tools=[
        Tool(
            name="write_document",
            description="Write a document",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["title", "content"],
            },
            execute=write_document,
        )
    ],
)


async def main():
    bus = Bus()
    log = EventLog()
    orch = Orchestrator(bus, log)
    orch.add_agent(researcher)
    orch.add_agent(writer)
    await bus.send(
        Message(sender="user", to="researcher", content="Research Tokyo's economy")
    )
    await orch.run()


asyncio.run(main())
