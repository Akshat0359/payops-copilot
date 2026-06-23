"""
Matching engine — runs 4 checks and creates ReconCase entries for detected issues.
"""
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models.payment import PaymentEvent
from models.settlement import Settlement, SettlementPayment
from models.refund import Refund
from models.chargeback import Chargeback
from models.bank_entry import BankStatementEntry
from models.case import ReconCase
from engine.exception_creator import create_case_if_not_exists
from engine.priority_scorer import compute_priority_score


async def run_matching_checks(
    db: AsyncSession,
    context_id: str = None,
) -> list[ReconCase]:
    """Run all 4 reconciliation checks. Returns newly created cases."""
    new_cases: list[ReconCase] = []

    new_cases.extend(await _check_missing_settlement(db))
    new_cases.extend(await _check_amount_mismatch(db))
    new_cases.extend(await _check_duplicate_refund(db))
    new_cases.extend(await _check_chargeback_risk(db))

    await db.flush()
    return new_cases


# ─────────────────────────────────────────────
# CHECK A — MISSING_SETTLEMENT
# ─────────────────────────────────────────────
async def _check_missing_settlement(db: AsyncSession) -> list[ReconCase]:
    cutoff = datetime.utcnow() - timedelta(hours=72)
    stmt = select(PaymentEvent).where(
        PaymentEvent.status == "captured",
        PaymentEvent.created_at < cutoff,
    )
    result = await db.execute(stmt)
    payments = result.scalars().all()

    created = []
    for payment in payments:
        # Check if settlement link exists
        link_stmt = select(SettlementPayment).where(
            SettlementPayment.payment_id == payment.id
        )
        link_result = await db.execute(link_stmt)
        link = link_result.scalars().first()
        if link:
            continue

        score = compute_priority_score(payment.amount_paise, payment.created_at)
        case = await create_case_if_not_exists(
            db,
            case_type="MISSING_SETTLEMENT",
            merchant_id=payment.merchant_id,
            payment_id=payment.id,
            discrepancy_paise=payment.amount_paise,
            priority_score=score,
        )
        if case:
            created.append(case)

    return created


# ─────────────────────────────────────────────
# CHECK B — AMOUNT_MISMATCH
# ─────────────────────────────────────────────
async def _check_amount_mismatch(db: AsyncSession) -> list[ReconCase]:
    stmt = select(BankStatementEntry).where(
        BankStatementEntry.matched_settlement_id.is_(None),
        BankStatementEntry.utr.is_not(None),
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    created = []
    for entry in entries:
        # Find matching settlement by UTR
        settle_stmt = select(Settlement).where(Settlement.utr == entry.utr)
        settle_result = await db.execute(settle_stmt)
        settlement = settle_result.scalars().first()
        if not settlement:
            continue

        diff = abs(entry.amount_paise - settlement.amount_paise)
        if diff <= 200:
            # Mark as matched even if within tolerance
            entry.matched_settlement_id = settlement.id
            entry.matched_at = datetime.utcnow()
            continue

        # Mark matched but create mismatch case
        entry.matched_settlement_id = settlement.id
        entry.matched_at = datetime.utcnow()

        score = compute_priority_score(
            settlement.amount_paise,
            settlement.created_at,
        )
        case = await create_case_if_not_exists(
            db,
            case_type="AMOUNT_MISMATCH",
            merchant_id=settlement.merchant_id,
            settlement_id=settlement.id,
            discrepancy_paise=diff,
            priority_score=score,
        )
        if case:
            created.append(case)

    return created


# ─────────────────────────────────────────────
# CHECK C — DUPLICATE_REFUND
# ─────────────────────────────────────────────
async def _check_duplicate_refund(db: AsyncSession) -> list[ReconCase]:
    stmt = (
        select(Refund.payment_id, func.count(Refund.id).label("cnt"))
        .where(Refund.status == "processed")
        .group_by(Refund.payment_id)
        .having(func.count(Refund.id) > 1)
    )
    result = await db.execute(stmt)
    rows = result.all()

    created = []
    for row in rows:
        payment_id = row.payment_id

        # Get payment to find merchant
        pay_stmt = select(PaymentEvent).where(PaymentEvent.id == payment_id)
        pay_result = await db.execute(pay_stmt)
        payment = pay_result.scalars().first()
        merchant_id = payment.merchant_id if payment else "unknown"

        case = await create_case_if_not_exists(
            db,
            case_type="DUPLICATE_REFUND",
            merchant_id=merchant_id,
            payment_id=payment_id,
            priority_score=100,
        )
        if case:
            created.append(case)

    return created


# ─────────────────────────────────────────────
# CHECK D — CHARGEBACK_RISK
# ─────────────────────────────────────────────
async def _check_chargeback_risk(db: AsyncSession) -> list[ReconCase]:
    deadline_threshold = datetime.utcnow() + timedelta(hours=48)
    stmt = select(Chargeback).where(
        Chargeback.status == "open",
        Chargeback.evidence_submitted == False,  # noqa: E712
        Chargeback.respond_by <= deadline_threshold,
    )
    result = await db.execute(stmt)
    chargebacks = result.scalars().all()

    created = []
    for cb in chargebacks:
        # Get payment to find merchant
        pay_stmt = select(PaymentEvent).where(PaymentEvent.id == cb.payment_id)
        pay_result = await db.execute(pay_stmt)
        payment = pay_result.scalars().first()
        merchant_id = payment.merchant_id if payment else "unknown"

        score = compute_priority_score(
            cb.amount_paise,
            cb.created_at,
            respond_by=cb.respond_by,
        )
        case = await create_case_if_not_exists(
            db,
            case_type="CHARGEBACK_RISK",
            merchant_id=merchant_id,
            payment_id=cb.payment_id,
            chargeback_id=cb.id,
            discrepancy_paise=cb.amount_paise,
            priority_score=score,
        )
        if case:
            created.append(case)

    return created
