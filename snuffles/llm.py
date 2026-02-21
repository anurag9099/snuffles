"""LLM client supporting OpenAI-compatible APIs and AWS Bedrock."""

import json
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


# ---------------------------------------------------------------------------
# Bedrock (Anthropic Messages API via boto3)
# ---------------------------------------------------------------------------

def _openai_tools_to_anthropic(tools: list[dict]) -> list[dict]:
    """Convert OpenAI function-calling tool schemas to Anthropic format."""
    result = []
    for t in tools:
        fn = t["function"]
        result.append({
            "name": fn["name"],
            "description": fn.get("description", ""),
            "input_schema": fn.get("parameters", {"type": "object", "properties": {}}),
        })
    return result


def _openai_messages_to_anthropic(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Split OpenAI messages into (system, messages) for Anthropic format."""
    system = None
    converted = []
    for msg in messages:
        if msg["role"] == "system":
            system = msg["content"]
        elif msg["role"] == "user":
            converted.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant":
            content_blocks = []
            if msg.get("content"):
                content_blocks.append({"type": "text", "text": msg["content"]})
            for tc in msg.get("tool_calls") or []:
                content_blocks.append({
                    "type": "tool_use",
                    "id": tc["id"],
                    "name": tc["function"]["name"],
                    "input": json.loads(tc["function"]["arguments"]),
                })
            converted.append({"role": "assistant", "content": content_blocks})
        elif msg["role"] == "tool":
            converted.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": msg["content"],
                }],
            })
    return system, converted


async def _bedrock_chat_completion(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    region: str | None = None,
    profile: str | None = None,
) -> LLMResponse:
    """Call Anthropic model via AWS Bedrock using boto3."""
    import boto3

    region = region or os.environ.get("AWS_REGION", "us-east-1")
    session_kwargs = {}
    if profile:
        session_kwargs["profile_name"] = profile
    session = boto3.Session(region_name=region, **session_kwargs)
    client = session.client("bedrock-runtime", region_name=region)

    system, anthropic_messages = _openai_messages_to_anthropic(messages)

    body: dict = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 4096,
        "messages": anthropic_messages,
    }
    if system:
        body["system"] = system
    if tools:
        body["tools"] = _openai_tools_to_anthropic(tools)

    response = client.invoke_model(
        modelId=model,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(body),
    )
    data = json.loads(response["body"].read())

    # Parse Anthropic response format
    text_parts = []
    tool_calls = []
    for block in data.get("content", []):
        if block["type"] == "text":
            text_parts.append(block["text"])
        elif block["type"] == "tool_use":
            tool_calls.append(
                ToolCall(
                    id=block["id"],
                    function=FunctionCall(
                        name=block["name"],
                        arguments=json.dumps(block["input"]),
                    ),
                )
            )

    content = "\n".join(text_parts) if text_parts else None
    return LLMResponse(content=content, tool_calls=tool_calls)


# ---------------------------------------------------------------------------
# OpenAI-compatible
# ---------------------------------------------------------------------------

async def _openai_chat_completion(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
) -> LLMResponse:
    """Call any OpenAI-compatible API."""
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


# ---------------------------------------------------------------------------
# Unified entry point
# ---------------------------------------------------------------------------

async def chat_completion(
    model: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    api_key: str | None = None,
    base_url: str = "https://api.openai.com/v1",
    provider: str | None = None,
    region: str | None = None,
    profile: str | None = None,
) -> LLMResponse:
    """Call an LLM. Routes to Bedrock or OpenAI based on provider param.

    provider="bedrock" -> AWS Bedrock (boto3, Anthropic Messages API)
    provider=None      -> auto-detect from LLM_PROVIDER env var,
                          then fall back to OpenAI-compatible
    """
    provider = provider or os.environ.get("LLM_PROVIDER", "openai")

    if provider == "bedrock":
        return await _bedrock_chat_completion(
            model=model, messages=messages, tools=tools,
            region=region, profile=profile,
        )
    else:
        return await _openai_chat_completion(
            model=model, messages=messages, tools=tools,
            api_key=api_key, base_url=base_url,
        )
