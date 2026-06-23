"""
Tests for the dispute agent.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from models.case import ReconCase
from models.chargeback import Chargeback


async def _setup_dispute_case(db, hours_until_deadline=10):
    """Helper to create a chargeback + case for testing."""
    respond_by = datetime.utcnow() + timedelta(hours=hours_until_deadline)

    from models.payment import PaymentEvent
    p = PaymentEvent(
        id="pay_dispute_001",
        order_id="order_d001",
        merchant_id="merchant_test",
        amount_paise=50000,
        currency="INR",
        status="captured",
        created_at=datetime.utcnow() - timedelta(days=1),
    )
    db.add(p)
    await db.flush()
    await db.refresh(p)

    cb = Chargeback(
        id="cb_test_001",
        payment_id="pay_dispute_001",
        amount_paise=50000,
        reason_code="UA",
        reason_description="Unauthorized transaction",
        status="open",
        phase="chargeback",
        respond_by=respond_by,
        evidence_submitted=False,
        created_at=datetime.utcnow() - timedelta(hours=4),
    )
    db.add(cb)
    await db.flush()
    await db.refresh(cb)

    case = ReconCase(
        case_type="CHARGEBACK_RISK",
        merchant_id="merchant_test",
        payment_id="pay_dispute_001",
        chargeback_id="cb_test_001",
        discrepancy_paise=50000,
        priority_score=100,
        status="open",
        created_at=datetime.utcnow() - timedelta(hours=4),
    )
    db.add(case)
    await db.flush()
    await db.refresh(case)  # populate autoincrement id
    return case


async def test_deadline_critical_prefix(db_session):
    """Dispute with respond_by in 10h should have DEADLINE CRITICAL prefix."""
    case = await _setup_dispute_case(db_session, hours_until_deadline=10)

    expected_text = (
        "ROOT CAUSE: Customer filed unauthorized transaction claim.\n"
        "WIN PROBABILITY: 0.7\n"
        "EVIDENCE NEEDED:\n"
        "- Transaction logs\n"
        "- IP address records\n"
        "RESOLUTION STEPS:\n"
        "1. Gather evidence immediately.\n"
        "2. Submit to payment processor.\n"
        "3. Follow up.\n"
        "confidence: 0.75"
    )

    # Gemini response format
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

    with (
        patch("agents.base.httpx.AsyncClient", return_value=mock_client),
        patch("agents.base.settings") as mock_settings,
    ):
        mock_settings.active_provider = "gemini"
        mock_settings.has_ai_key = True
        mock_settings.gemini_api_key = "test-key"
        mock_settings.gemini_model = "gemini-2.0-flash"

        from agents.dispute_agent import analyze_dispute_case
        result = await analyze_dispute_case(case.id, db_session)

    # Re-fetch case
    from sqlalchemy import select
    from models.case import ReconCase as RC
    refreshed = await db_session.execute(select(RC).where(RC.id == case.id))
    updated_case = refreshed.scalars().first()

    assert updated_case is not None
    assert updated_case.ai_root_cause is not None
    assert "DEADLINE CRITICAL" in updated_case.ai_root_cause


async def test_priority_score_100_for_urgent(db_session):
    """Chargeback with <24h deadline should result in priority_score 100."""
    from engine.priority_scorer import compute_priority_score

    respond_by = datetime.utcnow() + timedelta(hours=10)
    score = compute_priority_score(
        amount_paise=50000,
        created_at=datetime.utcnow() - timedelta(hours=4),
        respond_by=respond_by,
    )
    assert score == 100
