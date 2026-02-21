"""The core agent loop: think -> act -> observe.

A plain async function. Not a class method, not a generator.
Every step emits an Event for full transparency.
"""

import json

from snuffles.message import Message, Event
from snuffles.agent import Agent
from snuffles.llm import chat_completion
from snuffles.log import EventLog


async def run_loop(
    agent: Agent,
    trigger_message: Message,
    event_log: EventLog,
) -> Message | None:
    """The core agent loop: think -> act -> observe.

    Returns the agent's final response as a Message, or None.
    """

    messages = [
        {"role": "system", "content": agent.instructions},
        {"role": "user", "content": trigger_message.content},
    ]

    event_log.record(
        Event(
            kind="loop_start",
            agent=agent.name,
            data={"trigger": trigger_message.content[:200]},
        )
    )

    for iteration in range(1, agent.max_iterations + 1):

        # THINK: Ask the LLM what to do
        event_log.record(
            Event(
                kind="llm_call",
                agent=agent.name,
                data={"iteration": iteration, "message_count": len(messages)},
            )
        )

        response = await chat_completion(
            model=agent.model,
            messages=messages,
            tools=agent.tool_schemas() if agent.tools else None,
        )

        # If no tool calls -> done
        if not response.tool_calls:
            event_log.record(
                Event(
                    kind="llm_response",
                    agent=agent.name,
                    data={"content": (response.content or "")[:500]},
                )
            )
            return Message(
                sender=agent.name,
                to=trigger_message.sender,
                content=response.content or "",
            )

        # ACT: Execute each tool call
        messages.append(response.to_message_dict())

        for tool_call in response.tool_calls:
            tool = agent.get_tool(tool_call.function.name)

            event_log.record(
                Event(
                    kind="tool_call",
                    agent=agent.name,
                    data={
                        "tool": tool_call.function.name,
                        "args": tool_call.function.arguments,
                        "iteration": iteration,
                    },
                )
            )

            if tool is None:
                result = f"Error: unknown tool '{tool_call.function.name}'"
            else:
                try:
                    args = json.loads(tool_call.function.arguments)
                    result = await tool.execute(**args)
                except Exception as e:
                    result = f"Error: {e}"

            # OBSERVE: Feed result back to LLM
            event_log.record(
                Event(
                    kind="tool_result",
                    agent=agent.name,
                    data={
                        "tool": tool_call.function.name,
                        "result": result[:500],
                        "iteration": iteration,
                    },
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

    # Safety: hit max iterations
    event_log.record(
        Event(
            kind="loop_max_iterations",
            agent=agent.name,
            data={"iterations": agent.max_iterations},
        )
    )
    return Message(
        sender=agent.name,
        to=trigger_message.sender,
        content="I reached my iteration limit.",
    )
