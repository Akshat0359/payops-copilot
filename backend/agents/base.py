"""
Base agent runner — provider-agnostic.
Primary: Gemini (GEMINI_API_KEY)
Fallback: Anthropic (ANTHROPIC_API_KEY)
Graceful degradation: structured fallback if no key is set.
"""
import re
import json
from dataclasses import dataclass, field

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


@dataclass
class AgentResult:
    text: str
    tools_called: list[str] = field(default_factory=list)
    confidence: float = 0.5
    error: str | None = None


def _parse_confidence(text: str) -> float:
    match = re.search(r"confidence:\s*([0-9.]+)", text, re.IGNORECASE)
    if match:
        return max(0.0, min(1.0, float(match.group(1))))
    return 0.5


# ─────────────────────────────────────────────
# GEMINI ADAPTER
# ─────────────────────────────────────────────

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def _run_gemini(
    system_prompt: str,
    user_message: str,
    client: httpx.AsyncClient,
) -> AgentResult:
    """
    Single-shot Gemini generateContent call.
    Gemini doesn't support multi-turn tool-use the same way as Anthropic,
    so we include all context in a rich system+user prompt and parse structured output.
    """
    model = settings.gemini_model or "gemini-2.0-flash"
    url = f"{GEMINI_BASE_URL}/{model}:generateContent"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_message}],
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1024,
            "topP": 0.95,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
    }

    response = await client.post(
        url,
        headers={
            "Content-Type": "application/json",
            "X-goog-api-key": settings.gemini_api_key,
        },
        json=payload,
        timeout=45.0,
    )

    if response.status_code != 200:
        return AgentResult(
            text="",
            confidence=0.0,
            error=f"Gemini API error {response.status_code}: {response.text[:500]}",
        )

    data = response.json()

    # Parse Gemini response: candidates[0].content.parts[0].text
    try:
        candidates = data.get("candidates", [])
        if not candidates:
            return AgentResult(
                text="",
                confidence=0.0,
                error="Gemini returned no candidates",
            )
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts)
        finish_reason = candidates[0].get("finishReason", "")

        if not text:
            return AgentResult(
                text="",
                confidence=0.0,
                error=f"Gemini returned empty content (finishReason={finish_reason})",
            )

        confidence = _parse_confidence(text)
        return AgentResult(text=text, confidence=confidence)

    except (KeyError, IndexError, TypeError) as e:
        return AgentResult(
            text="",
            confidence=0.0,
            error=f"Gemini response parse error: {e}. Raw: {str(data)[:300]}",
        )


# ─────────────────────────────────────────────
# ANTHROPIC ADAPTER (fallback)
# ─────────────────────────────────────────────

async def _run_anthropic(
    system_prompt: str,
    user_message: str,
    client: httpx.AsyncClient,
    max_iterations: int = 5,
) -> AgentResult:
    """
    Anthropic Claude multi-turn tool-use loop (legacy fallback).
    """
    # Import here to avoid circular deps if tools module changes
    from agents.tools import TOOL_DEFINITIONS, execute_tool

    messages = [{"role": "user", "content": user_message}]
    tools_called: list[str] = []

    for _ in range(max_iterations):
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": settings.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1000,
                "system": system_prompt,
                "tools": TOOL_DEFINITIONS,
                "messages": messages,
            },
            timeout=30.0,
        )

        if response.status_code != 200:
            return AgentResult(
                text="",
                tools_called=tools_called,
                confidence=0.0,
                error=f"Anthropic API error {response.status_code}: {response.text[:500]}",
            )

        data = response.json()
        stop_reason = data.get("stop_reason")

        if stop_reason == "end_turn":
            text = next(
                (b["text"] for b in data["content"] if b.get("type") == "text"),
                "",
            )
            return AgentResult(
                text=text,
                tools_called=tools_called,
                confidence=_parse_confidence(text),
            )

        if stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": data["content"]})
            tool_results = []
            for block in data["content"]:
                if block.get("type") == "tool_use":
                    tools_called.append(block["name"])
                    # execute_tool needs db — pass through closure won't work here
                    # This is handled by the caller; we'd need db passed in
                    # For fallback mode, skip tool execution gracefully
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block["id"],
                            "content": json.dumps({"error": "tool execution skipped in fallback"}),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
            continue

        break

    return AgentResult(
        text="Agent did not complete.",
        tools_called=tools_called,
        confidence=0.3,
    )


# ─────────────────────────────────────────────
# PUBLIC INTERFACE
# ─────────────────────────────────────────────

async def run_agent(
    system_prompt: str,
    user_message: str,
    db: AsyncSession,
    max_iterations: int = 5,
) -> AgentResult:
    """
    Provider-agnostic agent runner.
    Prefers Gemini if GEMINI_API_KEY is set; falls back to Anthropic.
    Returns a graceful error AgentResult if no provider is configured.
    """
    provider = settings.active_provider

    if provider is None:
        return AgentResult(
            text="",
            confidence=0.0,
            error="No AI provider configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in backend/.env",
        )

    async with httpx.AsyncClient() as client:
        if provider == "gemini":
            return await _run_gemini(system_prompt, user_message, client)
        else:
            return await _run_anthropic(system_prompt, user_message, client, max_iterations)
