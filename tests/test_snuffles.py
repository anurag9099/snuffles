import asyncio
import json
import unittest
from unittest.mock import patch

from snuffles import Agent, Bus, EventLog, Message, Orchestrator
from snuffles.llm import LLMResponse
from snuffles.loop import run_loop


def response_queue(*responses: LLMResponse):
    remaining = list(responses)

    async def fake_chat_completion(*args, **kwargs):
        if not remaining:
            raise AssertionError("No more fake responses queued")
        return remaining.pop(0)

    return fake_chat_completion


class SnufflesTests(unittest.IsolatedAsyncioTestCase):
    async def test_plain_text_response_returns_to_original_sender(self):
        agent = Agent(name="assistant", instructions="Be helpful.")
        trigger = Message(sender="user", to="assistant", content="Hello")
        log = EventLog()

        with patch(
            "snuffles.loop.chat_completion",
            new=response_queue(LLMResponse(content="Hi there")),
        ):
            reply = await run_loop(agent, trigger, log)

        self.assertIsNotNone(reply)
        self.assertEqual(reply.sender, "assistant")
        self.assertEqual(reply.to, "user")
        self.assertEqual(reply.content, "Hi there")
        self.assertEqual(log.events[-1].kind, "loop_end")
        self.assertEqual(log.events[-1].data["to"], "user")

    async def test_json_envelope_routes_to_another_agent(self):
        bus = Bus()
        log = EventLog()
        orch = Orchestrator(bus, log)
        orch.add_agent(Agent(name="researcher", instructions="Research"))
        orch.add_agent(Agent(name="writer", instructions="Write"))

        with patch(
            "snuffles.loop.chat_completion",
            new=response_queue(
                LLMResponse(
                    content=json.dumps(
                        {"to": "writer", "content": "Research handoff"}
                    )
                ),
                LLMResponse(
                    content=json.dumps(
                        {"to": "user", "content": "Final answer"}
                    )
                ),
            ),
        ):
            run_task = asyncio.create_task(orch.run())
            try:
                await bus.send(
                    Message(sender="user", to="researcher", content="Research Tokyo")
                )
                first = await asyncio.wait_for(bus.next_reply(), timeout=1)
                second = await asyncio.wait_for(bus.next_reply(), timeout=1)
            finally:
                orch.stop()
                await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual((first.sender, first.to), ("researcher", "writer"))
        self.assertEqual(first.content, "Research handoff")
        self.assertEqual((second.sender, second.to), ("writer", "user"))
        self.assertEqual(second.content, "Final answer")

    async def test_manager_calculator_delegation_chain_completes(self):
        bus = Bus()
        log = EventLog()
        orch = Orchestrator(bus, log)
        orch.add_agent(Agent(name="manager", instructions="Delegate math"))
        orch.add_agent(Agent(name="calculator", instructions="Do math"))

        with patch(
            "snuffles.loop.chat_completion",
            new=response_queue(
                LLMResponse(
                    content=json.dumps(
                        {"to": "calculator", "content": "42 * 17 + 256"}
                    )
                ),
                LLMResponse(content="970"),
                LLMResponse(
                    content=json.dumps(
                        {"to": "user", "content": "42 * 17 + 256 = 970"}
                    )
                ),
            ),
        ):
            run_task = asyncio.create_task(orch.run())
            try:
                await bus.send(
                    Message(
                        sender="user",
                        to="manager",
                        content="What is 42 * 17 + 256?",
                    )
                )
                first = await asyncio.wait_for(bus.next_reply(), timeout=1)
                second = await asyncio.wait_for(bus.next_reply(), timeout=1)
                third = await asyncio.wait_for(bus.next_reply(), timeout=1)
            finally:
                orch.stop()
                await asyncio.wait_for(run_task, timeout=1)

        self.assertEqual((first.sender, first.to), ("manager", "calculator"))
        self.assertEqual(first.content, "42 * 17 + 256")
        self.assertEqual((second.sender, second.to), ("calculator", "manager"))
        self.assertEqual(second.content, "970")
        self.assertEqual((third.sender, third.to), ("manager", "user"))
        self.assertEqual(third.content, "42 * 17 + 256 = 970")

    async def test_orchestrator_stop_exits_while_idle(self):
        bus = Bus()
        orch = Orchestrator(bus, EventLog())

        run_task = asyncio.create_task(orch.run())
        await asyncio.sleep(0)
        orch.stop()
        await asyncio.wait_for(run_task, timeout=1)


if __name__ == "__main__":
    unittest.main()
