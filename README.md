<div align="center">

<img src="https://static.wikia.nocookie.net/animated-dogs/images/2/23/49-494035_snuffles-snowball-rickandmorty-freetoedit-snowball-rick-and-morty.png/revision/latest?cb=20210408002317" alt="Snuffles" width="300"/>

*"Where are my testicles, Summer?"*

**The simplest multi-agent system. ~570 lines of core Python.**

Small enough to read in an evening.

Snuffles is a compact repo for learning how agents work:
messages, prompts, tool calls, routing, and event logs. The goal is
to show the mechanics without hiding them behind a large framework.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Dependencies: httpx](https://img.shields.io/badge/dependencies-httpx-green.svg)](https://www.python-httpx.org/)

</div>

---

## Quick Start

OpenAI-compatible API:

```bash
cd snuffles
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

export OPENAI_API_KEY="sk-..."
# Optional: defaults to gpt-4.1-mini
export LLM_MODEL="gpt-4.1-mini"

python examples/01_single_agent.py
```

Local OpenAI-compatible model (Ollama, LM Studio, vLLM, etc.):

```bash
export OPENAI_BASE_URL="http://localhost:11434/v1"
export OPENAI_API_KEY="unused"
export LLM_MODEL="<local-model-name>"

python examples/01_single_agent.py
```

Optional AWS Bedrock path:

```bash
pip install boto3

export LLM_PROVIDER="bedrock"
export AWS_REGION="us-east-1"
export AWS_PROFILE="<your-profile>"
export LLM_MODEL="<bedrock-model-id>"

python examples/01_single_agent.py
```

---

## Read The Code In This Order

1. `snuffles/message.py` — what a message is, and what gets logged as an event
2. `snuffles/agent.py` — the whole agent definition: name, instructions, tools, model
3. `snuffles/bus.py` — the two queues that move messages around
4. `snuffles/loop.py` — the actual think -> act -> observe loop
5. `snuffles/orchestrator.py` — message routing and agent-to-agent re-injection
6. `snuffles/trigger.py`, `snuffles/log.py`, `snuffles/llm.py` — proactive wakeups, logging, and provider glue

If you only read two files, read `loop.py` and `orchestrator.py`.

---

## The Five Primitives

| Primitive | File | What it means |
|-----------|------|---------------|
| **Message** | `message.py` | A unit of communication: `sender`, `to`, `content`, `timestamp` |
| **Agent** | `agent.py` | Identity plus instructions plus tools |
| **Bus** | `bus.py` | The inbound and outbound queues |
| **Loop** | `loop.py` | Ask the LLM, run tools, feed tool results back |
| **Trigger** | `trigger.py` | Wake an agent on a timer or file change |

Supporting modules:

| File | Role |
|------|------|
| `orchestrator.py` | Pull messages from the bus, route them, and re-inject agent-to-agent replies |
| `llm.py` | Thin provider layer for OpenAI-compatible APIs and Bedrock |
| `log.py` | Stdout plus optional JSONL event log |

---

## File Structure

```text
snuffles/
├── snuffles/
│   ├── message.py
│   ├── agent.py
│   ├── bus.py
│   ├── loop.py
│   ├── trigger.py
│   ├── orchestrator.py
│   ├── llm.py
│   └── log.py
├── examples/
│   ├── 01_single_agent.py
│   ├── 02_proactive.py
│   ├── 03_two_agents.py
│   └── 04_delegation.py
└── pyproject.toml
```

---

## One Request Walkthrough

When you send:

```python
await bus.send(Message(sender="user", to="assistant", content="What is Tokyo's population?"))
```

Snuffles does exactly this:

1. `Bus.send()` puts the message on the inbound queue.
2. `Orchestrator.run()` receives it and logs `message_routed`.
3. `run_loop()` builds a conversation with:
   - the agent instructions as the system message
   - the inbound message content as the user message
4. The loop calls the LLM.
5. If the LLM asks for tools, Snuffles executes them and appends the tool results.
6. When the LLM returns final text:
   - plain text replies to the original sender
   - a JSON envelope can route to someone else
7. The orchestrator publishes the outbound `Message`.
8. If that message targets another agent, it gets re-injected into the inbound queue.

The examples start `orch.run()` in the background, wait for outbound replies, then
call `orch.stop()` so the script exits cleanly after the lesson is over.

---

## Explicit Routing Envelope

Snuffles supports one explicit routing convention for final model responses:

```json
{"to": "writer", "content": "Summarize these research notes into a final answer."}
```

If the final model response is valid JSON with string `to` and `content` fields,
Snuffles turns it into the final outbound `Message`.

If the final model response is anything else, Snuffles falls back to:

```text
to = trigger_message.sender
content = response.content
```

This keeps routing explicit. There is no planner layer or built-in
message-sending tool.

---

## Examples

- `examples/01_single_agent.py` — one agent, one tool, one reply, then clean shutdown
- `examples/02_proactive.py` — timer-driven agent; this one is intentionally long-running
- `examples/03_two_agents.py` — `researcher -> writer -> user` with explicit JSON routing
- `examples/04_delegation.py` — `user -> manager -> calculator -> manager -> user`

---

## Event Log Output

Every important step is printed to stdout and can also be written to JSONL:

```text
[14:32:01.234] message_routed       |              | from=user, to=assistant, content=What is Tokyo's population?
[14:32:01.235] loop_start           | assistant    | trigger=What is Tokyo's population?
[14:32:01.236] llm_call             | assistant    | iteration=1, message_count=2
[14:32:02.891] tool_call            | assistant    | tool=web_search, args={"query":"Tokyo population"}
[14:32:03.456] tool_result          | assistant    | tool=web_search, result=Tokyo has 13.96M people
[14:32:03.457] llm_call             | assistant    | iteration=2, message_count=4
[14:32:04.123] llm_response         | assistant    | content=The population of Tokyo is approximately 13.96M
[14:32:04.124] loop_end             | assistant    | to=user, content=The population of Tokyo is approximately 13.96M
```

Write to a file:

```python
from pathlib import Path

log = EventLog(path=Path("events.jsonl"))
```

Then inspect it:

```bash
cat events.jsonl | jq 'select(.kind == "tool_call")'
cat events.jsonl | jq 'select(.agent == "researcher")'
grep loop_end events.jsonl
```

---

## What Snuffles Intentionally Does Not Do Yet

- No persistent memory across turns
- No planner or task graph layer
- No retries, backoff, or production guardrails
- No extra lifecycle framework beyond the few primitives above
- No GUI or playground in the core repo

This is intentional. Start with the basics first.
