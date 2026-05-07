"""
Multi-provider LLM client.

Supports: Anthropic (Claude), OpenAI (GPT), DeepSeek, OpenRouter, Ollama
All providers use OpenAI-compatible API format via httpx for consistency.
"""

import json
import httpx
from typing import Any
from app.config import settings

# Provider -> (base_url, model_key_in_settings)
PROVIDERS = {
    "anthropic": {
        "chat_url": "https://api.anthropic.com/v1/messages",
        "api_key_header": "x-api-key",
        "api_key": settings.anthropic_api_key,
    },
    "openai": {
        "chat_url": "https://api.openai.com/v1/chat/completions",
        "api_key_header": "Authorization",
        "api_key": settings.openai_api_key,
    },
    "deepseek": {
        "chat_url": "https://api.deepseek.com/v1/chat/completions",
        "api_key_header": "Authorization",
        "api_key": settings.deepseek_api_key,
    },
    "openrouter": {
        "chat_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key_header": "Authorization",
        "api_key": settings.openrouter_api_key,
    },
    "ollama": {
        "chat_url": f"{settings.ollama_base_url}/v1/chat/completions",
        "api_key_header": "",
        "api_key": "",
    },
}


def _get_provider_config() -> dict:
    cfg = PROVIDERS.get(settings.llm_provider)
    if not cfg:
        raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
    return cfg


def _build_headers(provider_cfg: dict) -> dict:
    headers = {"Content-Type": "application/json"}
    key_header = provider_cfg.get("api_key_header", "")
    api_key = provider_cfg.get("api_key", "")
    if key_header and api_key:
        if key_header == "Authorization":
            headers[key_header] = f"Bearer {api_key}"
        else:
            headers[key_header] = api_key
    # Anthropic requires anthropic-version header
    if settings.llm_provider == "anthropic":
        headers["anthropic-version"] = "2023-06-01"
    return headers


def _build_chat_payload(messages: list[dict], tools: list[dict], system_prompt: str = "") -> dict:
    """Build payload in OpenAI-compatible format."""
    payload = {
        "model": settings.active_model,
        "messages": messages,
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
    if system_prompt:
        # Insert system message at the beginning
        payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]
    return payload


def _build_anthropic_payload(messages: list[dict], tools: list[dict], system_prompt: str = "") -> dict:
    """Anthropic uses a different API format — convert."""
    # Anthropic: system as top-level param, messages without system role
    filtered = [m for m in messages if m.get("role") != "system"]
    payload = {
        "model": settings.active_model,
        "messages": filtered,
        "max_tokens": 4096,
        "temperature": 0.3,
    }
    if system_prompt:
        payload["system"] = system_prompt
    if tools:
        payload["tools"] = tools
    return payload


def _extract_response_text(data: dict) -> str:
    """Extract text from provider response (handles OpenAI and Anthropic formats)."""
    # OpenAI format
    if "choices" in data:
        choice = data["choices"][0]
        if "message" in choice and "content" in choice["message"] and choice["message"]["content"]:
            return choice["message"]["content"]
    # Anthropic format
    if "content" in data:
        text_parts = [block["text"] for block in data["content"] if block["type"] == "text"]
        return "".join(text_parts)
    return ""


def _extract_tool_calls(data: dict) -> list[dict]:
    """Extract tool calls from provider response."""
    # OpenAI format
    if "choices" in data:
        msg = data["choices"][0].get("message", {})
        raw = msg.get("tool_calls") or []
        return [
            {
                "id": tc.get("id", ""),
                "type": "function",
                "function": {
                    "name": tc["function"]["name"],
                    "arguments": tc["function"].get("arguments", "{}"),
                },
            }
            for tc in raw
        ]
    # Anthropic format
    if "content" in data:
        return [
            {
                "id": block.get("id", ""),
                "type": "tool_use",
                "name": block.get("name", ""),
                "input": block.get("input", {}),
            }
            for block in data["content"]
            if block.get("type") == "tool_use"
        ]
    return []


async def chat_completion(
    messages: list[dict],
    tools: list[dict] | None = None,
    system_prompt: str = "",
) -> dict:
    """
    Send a chat completion request to the configured LLM provider.
    Returns: {"content": str, "tool_calls": list[dict]}
    """
    cfg = _get_provider_config()
    headers = _build_headers(cfg)

    if settings.llm_provider == "anthropic":
        payload = _build_anthropic_payload(messages, tools or [], system_prompt)
    else:
        payload = _build_chat_payload(messages, tools or [], system_prompt)

    timeout = 120.0 if settings.llm_provider == "ollama" else 60.0
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(cfg["chat_url"], json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(
            f"LLM API error ({settings.llm_provider}): {resp.status_code} - {resp.text[:500]}"
        )

    data = resp.json()
    content = _extract_response_text(data)
    tool_calls = _extract_tool_calls(data)

    return {"content": content, "tool_calls": tool_calls}
