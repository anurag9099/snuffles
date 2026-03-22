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
    instructions="""You are a manager.
    If the user asks a math question, send only the arithmetic expression
    to the 'calculator' agent with a JSON object like:
    {"to": "calculator", "content": "42 * 17 + 256"}
    If you receive a calculation result, respond to the user with a JSON object like:
    {"to": "user", "content": "42 * 17 + 256 = 970"}
    Return only the JSON object.""",
)

calculator = Agent(
    name="calculator",
    instructions="""You perform calculations. Use the calculate tool.
    Reply with plain text only, for example: 970""",
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
    run_task = asyncio.create_task(orch.run())

    try:
        await bus.send(
            Message(
                sender="user", to="manager", content="What is 42 * 17 + 256?"
            )
        )
        while True:
            reply = await bus.next_reply()
            print(f"{reply.sender} -> {reply.to}: {reply.content}")
            if reply.to == "user":
                break
    finally:
        orch.stop()
        await run_task


asyncio.run(main())
