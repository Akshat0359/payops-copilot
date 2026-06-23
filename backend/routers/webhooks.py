"""
Razorpay webhook ingestion router.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from schemas.webhook import RazorpayWebhookPayload
from models.payment import PaymentEvent
from models.refund import Refund
from models.settlement import Settlement, SettlementPayment
from models.chargeback import Chargeback
from engine.matcher import run_matching_checks

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/razorpay")
async def razorpay_webhook(
    body: RazorpayWebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    event = body.event
    payload = body.payload

    if event == "payment.captured" and payload.payment:
        entity = payload.payment.entity
        existing = await db.execute(
            select(PaymentEvent).where(PaymentEvent.id == entity.id)
        )
        payment = existing.scalars().first()
        if payment:
            payment.status = "captured"
        else:
            payment = PaymentEvent(
                id=entity.id,
                order_id=entity.order_id or "",
                merchant_id=entity.merchant_id or "unknown",
                amount_paise=entity.amount or 0,
                currency=entity.currency or "INR",
                status="captured",
                method=entity.method,
                bank=entity.bank,
                fee_paise=entity.fee,
                created_at=datetime.utcnow(),
            )
            db.add(payment)
        await db.flush()
        await run_matching_checks(db, context_id=entity.id)

    elif event == "refund.processed" and payload.refund:
        entity = payload.refund.entity
        existing = await db.execute(
            select(Refund).where(Refund.id == entity.id)
        )
        refund = existing.scalars().first()
        if refund:
            refund.status = "processed"
        else:
            refund = Refund(
                id=entity.id,
                payment_id=entity.payment_id,
                amount_paise=entity.amount or 0,
                status="processed",
                speed_requested=entity.speed_requested,
                created_at=datetime.utcnow(),
            )
            db.add(refund)
        await db.flush()
        await run_matching_checks(db, context_id=entity.payment_id)

    elif event == "settlement.processed" and payload.settlement:
        entity = payload.settlement.entity
        existing = await db.execute(
            select(Settlement).where(Settlement.id == entity.id)
        )
        settlement = existing.scalars().first()
        if not settlement:
            settlement = Settlement(
                id=entity.id,
                merchant_id=entity.merchant_id or "unknown",
                amount_paise=entity.amount or 0,
                fees_paise=entity.fees,
                utr=entity.utr,
                status=entity.status or "processed",
                settled_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(settlement)
        await db.flush()
        await run_matching_checks(db, context_id=entity.id)

    elif event == "dispute.created" and payload.dispute:
        entity = payload.dispute.entity
        existing = await db.execute(
            select(Chargeback).where(Chargeback.id == entity.id)
        )
        chargeback = existing.scalars().first()
        if not chargeback:
            chargeback = Chargeback(
                id=entity.id,
                payment_id=entity.payment_id,
                amount_paise=entity.amount or 0,
                reason_code=entity.reason_code,
                reason_description=entity.reason_description,
                status=entity.status or "open",
                phase=entity.phase,
                respond_by=datetime.utcnow() + timedelta(hours=72),
                evidence_submitted=False,
                created_at=datetime.utcnow(),
            )
            db.add(chargeback)
        await db.flush()
        await run_matching_checks(db, context_id=entity.id)

    return {"received": True, "event": event}
