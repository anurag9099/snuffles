"""A manager agent that delegates tasks to a worker agent."""

import asyncio
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, Message


async def calculate(expression: str) -> str:
    try:
        allowed = set("0123456789+-*/(). ")
        if not all(c in allowed for c in expression):
            return "Error: only arithmetic expressions allowed"
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"


manager = Agent(
    name="manager",
    instructions="""You are a manager. When asked complex questions,
    delegate calculation tasks to the 'calculator' agent by addressing
    your response to them.""",
)

calculator = Agent(
    name="calculator",
    instructions="You perform calculations. Use the calculate tool.",
    tools=[
        Tool(
            name="calculate",
            description="Evaluate a math expression",
            parameters={
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
            execute=calculate,
        )
    ],
)


async def main():
    bus = Bus()
    log = EventLog()
    orch = Orchestrator(bus, log)
    orch.add_agent(manager)
    orch.add_agent(calculator)
    await bus.send(
        Message(
            sender="user", to="manager", content="What is 42 * 17 + 256?"
        )
    )
    await orch.run()


asyncio.run(main())
