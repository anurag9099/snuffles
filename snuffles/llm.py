"""Thin OpenAI-compatible LLM client. One function, no provider abstraction."""

import os
from dataclasses import dataclass, field

import httpx


@dataclass
class FunctionCall:
    name: str
    arguments: str


@dataclass
class ToolCall:
    id: str
    function: FunctionCall


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_message_dict(self) -> dict:
        """Convert to OpenAI message format for conversation history."""
        msg: dict = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in self.tool_calls
            ]
        return msg


async def chat_completion(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
) -> LLMResponse:
    """Call any OpenAI-compatible API. One function. No provider abstraction."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
    base_url = os.environ.get("OPENAI_BASE_URL", base_url).rstrip("/")

    body: dict = {"model": model, "messages": messages}
    if tools:
        body["tools"] = tools

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    choice = data["choices"][0]["message"]
    tool_calls = []
    for tc in choice.get("tool_calls") or []:
        tool_calls.append(
            ToolCall(
                id=tc["id"],
                function=FunctionCall(
                    name=tc["function"]["name"],
                    arguments=tc["function"]["arguments"],
                ),
            )
        )

    return LLMResponse(content=choice.get("content"), tool_calls=tool_calls)
