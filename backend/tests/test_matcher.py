"""
Tests for the matching engine (matcher.py).
"""
import pytest
from datetime import datetime, timedelta

from models.payment import PaymentEvent
from models.settlement import Settlement, SettlementPayment
from models.refund import Refund
from models.bank_entry import BankStatementEntry
from models.case import ReconCase
from engine.matcher import run_matching_checks


async def _make_payment(db, pid="pay_test_001", amount=100_00, days_ago=5):
    p = PaymentEvent(
        id=pid,
        order_id=f"order_{pid}",
        merchant_id="merchant_test",
        amount_paise=amount,
        currency="INR",
        status="captured",
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(p)
    await db.flush()
    return p


async def test_missing_settlement_detected(db_session):
    """Payment older than 72h with no settlement should create a MISSING_SETTLEMENT case."""
    await _make_payment(db_session, pid="pay_ms_001", days_ago=5)
    cases = await run_matching_checks(db_session)
    assert any(c.case_type == "MISSING_SETTLEMENT" for c in cases)


async def test_no_false_positive_when_settled(db_session):
    """Payment with a settlement link should NOT create a MISSING_SETTLEMENT case."""
    payment = await _make_payment(db_session, pid="pay_ms_002", days_ago=5)

    settlement = Settlement(
        id="settle_001",
        merchant_id="merchant_test",
        amount_paise=9764,
        status="processed",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(settlement)
    await db_session.flush()

    link = SettlementPayment(
        settlement_id="settle_001",
        payment_id="pay_ms_002",
        amount_paise=9764,
    )
    db_session.add(link)
    await db_session.flush()

    cases = await run_matching_checks(db_session)
    missing = [c for c in cases if c.case_type == "MISSING_SETTLEMENT"]
    assert len(missing) == 0


async def test_amount_mismatch_detected(db_session):
    """Bank entry with wrong amount vs settlement should create AMOUNT_MISMATCH case."""
    settlement = Settlement(
        id="settle_am_001",
        merchant_id="merchant_test",
        amount_paise=50000,
        status="processed",
        utr="UTR_AM_001",
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    db_session.add(settlement)

    # Bank entry is off by 500 paise (₹5)
    entry = BankStatementEntry(
        account_id="TEST_ACCT",
        utr="UTR_AM_001",
        narration="Test entry",
        amount_paise=49500,  # 500 paise less
        direction="credit",
        transaction_date=datetime.utcnow().date(),
    )
    db_session.add(entry)
    await db_session.flush()

    cases = await run_matching_checks(db_session)
    mismatch = [c for c in cases if c.case_type == "AMOUNT_MISMATCH"]
    assert len(mismatch) >= 1
    assert mismatch[0].discrepancy_paise == 500


async def test_duplicate_refund_detected(db_session):
    """Two processed refunds for the same payment should create DUPLICATE_REFUND case."""
    payment = await _make_payment(db_session, pid="pay_dr_001", days_ago=5)

    for i in range(2):
        r = Refund(
            id=f"refund_dr_{i:03d}",
            payment_id="pay_dr_001",
            amount_paise=10000,
            status="processed",
            created_at=datetime.utcnow() - timedelta(hours=i),
        )
        db_session.add(r)
    await db_session.flush()

    cases = await run_matching_checks(db_session)
    dups = [c for c in cases if c.case_type == "DUPLICATE_REFUND"]
    assert len(dups) >= 1
