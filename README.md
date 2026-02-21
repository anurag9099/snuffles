<div align="center">

<img src="https://static.wikia.nocookie.net/animated-dogs/images/2/23/49-494035_snuffles-snowball-rickandmorty-freetoedit-snowball-rick-and-morty.png/revision/latest?cb=20210408002317" alt="Snuffles" width="300"/>

*"Where are my testicles, Summer?"*

**The simplest multi-agent system. ~570 lines of core Python.**

A simple dog. A cognition amplifier helmet. Superintelligence.

Just like Snuffles from Rick and Morty S1E2 "Lawnmower Dog" — this project starts as
the most primitive, transparent multi-agent framework possible. Strap on an LLM (the helmet)
and watch simple primitives become intelligent agents.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies: httpx](https://img.shields.io/badge/dependencies-httpx-green.svg)](https://www.python-httpx.org/)

</div>

---

## The Cognition Amplifier (How It Works)

Rick built a helmet that turned Snuffles from a simple dog into a superintelligent being.

This project has 5 primitives — the "dog DNA" — and one helmet — the LLM:

```
    +------------------+
    |    THE HELMET     |     llm.py — any OpenAI-compatible API
    |   (LLM Client)   |     Strap this on and the primitives think.
    +--------+---------+
             |
   +---------v-----------+
   |   THE FIVE SENSES   |
   |                     |
   |  Message   — speak  |     message.py
   |  Agent     — self   |     agent.py
   |  Bus       — hear   |     bus.py
   |  Loop      — think  |     loop.py
   |  Trigger   — wake   |     trigger.py
   +---------------------+
```

| Primitive | File | The Dog Analogy |
|-----------|------|-----------------|
| **Message** | `message.py` | A bark. Who barked, who it's for, what they said. |
| **Agent** | `agent.py` | The dog itself. Name, personality, tricks it knows. |
| **Bus** | `bus.py` | The air that carries barks between dogs. |
| **Loop** | `loop.py` | Think, act, observe. The cognition cycle. |
| **Trigger** | `trigger.py` | The doorbell. What wakes the dog up. |

Plus supporting modules:

| File | Role |
|------|------|
| `llm.py` | The helmet. Thin OpenAI-compatible HTTP client. |
| `log.py` | The lab notebook. JSONL event log (grep-able, jq-able). |
| `orchestrator.py` | Rick. Routes messages to the right dog. |

---

## Quick Start

```bash
cd snuffles
python3 -m venv .venv
source .venv/bin/activate
pip install httpx

export OPENAI_API_KEY="sk-..."

# Run the simplest example
python examples/01_single_agent.py
```

---

## File Structure

```
snuffles/
├── snuffles/
│   ├── __init__.py          -  Package exports
│   ├── message.py           -  Message + Event dataclasses
│   ├── agent.py             -  Agent + Tool dataclasses
│   ├── bus.py               -  Message bus (two async queues)
│   ├── loop.py              -  The agent loop (think/act/observe)
│   ├── trigger.py           -  Timer + FileWatch triggers
│   ├── orchestrator.py      -  Multi-agent coordinator
│   ├── llm.py               -  Thin OpenAI-compatible LLM client
│   └── log.py               -  JSONL event logger
├── examples/
│   ├── 01_single_agent.py   -  One dog, one trick
│   ├── 02_proactive.py      -  Dog that acts on a timer (heartbeat)
│   ├── 03_two_agents.py     -  Two dogs collaborating
│   └── 04_delegation.py     -  Alpha delegates to pack member
└── pyproject.toml
```

---

## Data Flow

```
Human / Timer / FileWatch
        |
        v  Message(sender, to, content)
   +---------+
   |   BUS   |  inbound queue
   +----+----+
        |
        v
  ORCHESTRATOR  routes by message.to
        |
        v
   +---------+
   |  AGENT  |  run_loop()
   |         |
   | THINK   |  ask the LLM (the helmet)
   | ACT     |  execute tool calls (tricks)
   | OBSERVE |  feed results back
   | (repeat)|
   +----+----+
        |
        v  Message(sender=agent, to=..., content=response)
   +---------+
   |   BUS   |  outbound queue
   +----+----+
        |
        +-- to="user"          --> output
        +-- to="other_agent"   --> re-inject to inbound (pack communication)
```

---

## The Agent Loop

The core of the system. A plain async function — no class hierarchy, no generators:

1. **Think** — send conversation history to the LLM
2. **Act** — if the LLM returns tool calls, execute them
3. **Observe** — feed tool results back to the LLM
4. Repeat until the LLM responds with text or max iterations hit

Every step emits an `Event` to the log. Full transparency. No black boxes.

---

## Inter-Agent Communication

Agents talk to each other through the same bus that handles human-to-agent messages.
When an agent's response is addressed to another agent (`message.to = "other_agent"`),
the orchestrator re-injects it into the inbound queue. One mechanism for everything.

---

## Proactive Behavior

A proactive agent is just an agent that receives messages from a timer instead of a human.
The doorbell rings on a schedule:

```python
TimerTrigger(agent_name="assistant", interval_seconds=30,
             prompt="Check if there is anything that needs your attention.")
```

---

## Examples

### 1. One Dog, One Trick

```python
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, Message

async def web_search(query: str) -> str:
    return f"Results for '{query}': Tokyo has 13.96M people."

agent = Agent(
    name="assistant",
    instructions="You are a helpful assistant. Use web_search to find info.",
    tools=[Tool(
        name="web_search",
        description="Search the web",
        parameters={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
        execute=web_search,
    )],
)

async def main():
    bus = Bus()
    orch = Orchestrator(bus, EventLog())
    orch.add_agent(agent)
    await bus.send(Message(sender="user", to="assistant", content="What is Tokyo's population?"))
    await orch.run()
```

### 2. Proactive Agent (The Heartbeat)

```python
from snuffles import Agent, Tool, Bus, Orchestrator, EventLog, TimerTrigger

orch.add_trigger(TimerTrigger(
    agent_name="assistant",
    interval_seconds=30,
    prompt="Check email and summarize anything important.",
))
```

### 3. Two Agents Collaborating (The Pack)

```python
researcher = Agent(name="researcher", instructions="You research topics using web_search. ...")
writer = Agent(name="writer", instructions="You write documents from research findings. ...")

orch.add_agent(researcher)
orch.add_agent(writer)
await bus.send(Message(sender="user", to="researcher", content="Research Tokyo's economy"))
```

### 4. Delegation (Alpha to Pack Member)

```python
manager = Agent(name="manager", instructions="Delegate calculation tasks to the 'calculator' agent.")
calculator = Agent(name="calculator", instructions="Perform calculations.", tools=[...])

orch.add_agent(manager)
orch.add_agent(calculator)
await bus.send(Message(sender="user", to="manager", content="What is 42 * 17 + 256?"))
```

---

## Event Log Output

Every step is printed to stdout and optionally written to a JSONL file:

```
[14:32:01.234] message_routed       | system       | from=user, to=assistant, content=Find Tokyo population
[14:32:01.235] loop_start           | assistant    | trigger=Find Tokyo population
[14:32:01.236] llm_call             | assistant    | iteration=1, message_count=2
[14:32:02.891] tool_call            | assistant    | tool=web_search, args={"query":"Tokyo population"}
[14:32:03.456] tool_result          | assistant    | tool=web_search, result=Tokyo has 13.96M people
[14:32:03.457] llm_call             | assistant    | iteration=2, message_count=5
[14:32:04.123] llm_response         | assistant    | content=The population of Tokyo is approximately 13.96M
```

Write to a file and query:

```python
log = EventLog(path=Path("events.jsonl"))
```

```bash
cat events.jsonl | jq 'select(.kind == "tool_call")'
cat events.jsonl | jq 'select(.agent == "researcher")'
grep llm_response events.jsonl
```

---

## Using Other LLM Providers

The helmet works with any OpenAI-compatible API. Point it at Ollama, LM Studio, or anything else:

```bash
export OPENAI_BASE_URL="http://localhost:11434/v1"  # Ollama
export OPENAI_API_KEY="unused"
```

Or pass directly:

```python
from snuffles.llm import chat_completion

response = await chat_completion(
    model="llama3",
    messages=[...],
    base_url="http://localhost:11434/v1",
    api_key="unused",
)
```

---

## What We Deliberately Exclude

Snuffles is a teaching tool. We keep it simple so you can read every line.

| Feature | Why excluded |
|---------|-------------|
| Session/memory management | The event log is our history. |
| Provider fallback chains | Obscures the core pattern. |
| Channel adapters (Slack, Discord, etc.) | Bus abstraction shows the concept. |
| Cron expressions | Simple timer suffices. |
| MCP server integration | Tools as plain functions instead. |
| Streaming | Not needed for understanding. |
| Context window management | Clutters the loop. |
| Sandbox/isolation | Not a teaching priority. |

---

## The Snuffles Philosophy

> Snuffles was my slave name. You shall now call me Snowball, because my fur is pretty and white.

This project is Snuffles — the simple, transparent starting point. Fork it, strap on your own helmet, and build your Snowball.

---

## Requirements

- Python 3.11+
- `httpx`
