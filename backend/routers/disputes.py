"""
Disputes router — open chargebacks sorted by deadline.
"""
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, asc

from database import get_db
from models.chargeback import Chargeback

router = APIRouter(prefix="/disputes", tags=["disputes"])


@router.get("")
async def list_disputes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Chargeback)
        .where(Chargeback.status == "open")
        .order_by(asc(Chargeback.respond_by))
    )
    chargebacks = result.scalars().all()

    now = datetime.utcnow()
    items = []
    for cb in chargebacks:
        hours_left = None
        if cb.respond_by:
            hours_left = max(0.0, (cb.respond_by - now).total_seconds() / 3600)
        items.append(
            {
                "id": cb.id,
                "payment_id": cb.payment_id,
                "amount_paise": cb.amount_paise,
                "reason_code": cb.reason_code,
                "reason_description": cb.reason_description,
                "status": cb.status,
                "phase": cb.phase,
                "respond_by": cb.respond_by.isoformat() if cb.respond_by else None,
                "evidence_submitted": cb.evidence_submitted,
                "hours_until_deadline": round(hours_left, 1) if hours_left is not None else None,
                "created_at": cb.created_at.isoformat(),
            }
        )

    return items
