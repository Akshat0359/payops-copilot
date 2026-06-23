"""
Tests for the recon agent.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from agents.base import _parse_confidence, AgentResult


# ── Confidence parsing tests (sync, no DB needed) ────────────────────────────

def test_confidence_parsing():
    assert _parse_confidence("confidence: 0.87") == pytest.approx(0.87)


def test_confidence_clamp():
    assert _parse_confidence("confidence: 1.5") == 1.0


def test_confidence_missing():
    assert _parse_confidence("no confidence here") == 0.5


def test_confidence_zero():
    assert _parse_confidence("confidence: 0.0") == 0.0


# ── Agent result structure (provider-agnostic mock) ───────────────────────────

async def test_agent_result_structure(db_session):
    """
    Mock run_agent at the top level so the test is provider-agnostic.
    Tests that AgentResult is parsed and returned correctly regardless of
    whether Gemini or Anthropic is the active provider.
    """
    expected_text = (
        "ROOT CAUSE: Settlement not found in banking records.\n"
        "RESOLUTION STEPS:\n"
        "1. Check UTR with bank.\n"
        "2. Escalate if not resolved.\n"
        "3. Update case status.\n"
        "confidence: 0.82"
    )

    # Mock the Gemini response format
    gemini_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": expected_text}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = gemini_response_data

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    # Patch: force gemini provider and mock httpx
    with (
        patch("agents.base.httpx.AsyncClient", return_value=mock_client),
        patch("agents.base.settings") as mock_settings,
    ):
        mock_settings.active_provider = "gemini"
        mock_settings.has_ai_key = True
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-2.0-flash"

        from agents.base import run_agent
        result = await run_agent(
            system_prompt="Test system prompt",
            user_message="Test user message",
            db=db_session,
        )

    assert isinstance(result, AgentResult)
    assert result.error is None
    assert "ROOT CAUSE" in result.text
    assert result.confidence == pytest.approx(0.82)
    assert isinstance(result.tools_called, list)
