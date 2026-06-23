"""
Exception creator helper — wraps the boilerplate of inserting a ReconCase
and checking for duplicates, so the matcher stays readable.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.case import ReconCase


async def create_case_if_not_exists(
    db: AsyncSession,
    *,
    case_type: str,
    merchant_id: str,
    payment_id: str | None = None,
    settlement_id: str | None = None,
    chargeback_id: str | None = None,
    discrepancy_paise: int | None = None,
    priority_score: int = 0,
) -> ReconCase | None:
    """
    Insert a new ReconCase only if an open case of the same type + payment_id
    does not already exist. Returns the new case or None if duplicate.
    """
    # Duplicate check — use the most specific available identifier
    stmt = select(ReconCase).where(
        ReconCase.case_type == case_type,
        ReconCase.status == "open",
    )
    if payment_id:
        stmt = stmt.where(ReconCase.payment_id == payment_id)
    elif settlement_id:
        stmt = stmt.where(ReconCase.settlement_id == settlement_id)
    if chargeback_id:
        stmt = stmt.where(ReconCase.chargeback_id == chargeback_id)

    result = await db.execute(stmt)
    existing = result.scalars().first()
    if existing:
        return None

    case = ReconCase(
        case_type=case_type,
        merchant_id=merchant_id,
        payment_id=payment_id,
        settlement_id=settlement_id,
        chargeback_id=chargeback_id,
        discrepancy_paise=discrepancy_paise,
        priority_score=priority_score,
        status="open",
        created_at=datetime.utcnow(),
    )
    db.add(case)
    await db.flush()  # get the autoincrement id
    return case
