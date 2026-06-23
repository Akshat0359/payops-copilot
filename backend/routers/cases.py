"""
Cases router — CRUD + AI analysis + HITL approve/reject.
"""
import math
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from database import get_db
from models.case import ReconCase, AuditLog
from models.payment import PaymentEvent
from models.chargeback import Chargeback
from schemas.case import CaseOut, CaseDetail, AuditLogOut
from agents.orchestrator import analyze_case
from config import settings

router = APIRouter(prefix="/cases", tags=["cases"])


def _case_to_detail(case: ReconCase, payment=None, chargeback=None, audit_logs=None) -> dict:
    data = {
        "id": case.id,
        "case_type": case.case_type,
        "merchant_id": case.merchant_id,
        "discrepancy_paise": case.discrepancy_paise,
        "priority_score": case.priority_score,
        "status": case.status,
        "ai_confidence": case.ai_confidence,
        "ai_root_cause": case.ai_root_cause,
        "ai_resolution_steps": case.ai_resolution_steps,
        "payment_id": case.payment_id,
        "settlement_id": case.settlement_id,
        "chargeback_id": case.chargeback_id,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "payment": None,
        "chargeback": None,
        "audit_log": [],
    }

    if payment:
        data["payment"] = {
            "id": payment.id,
            "order_id": payment.order_id,
            "merchant_id": payment.merchant_id,
            "amount_paise": payment.amount_paise,
            "currency": payment.currency,
            "status": payment.status,
            "method": payment.method,
            "bank": payment.bank,
            "fee_paise": payment.fee_paise,
            "captured_at": payment.captured_at.isoformat() if payment.captured_at else None,
            "created_at": payment.created_at.isoformat(),
        }

    if chargeback:
        hours_left = None
        if chargeback.respond_by:
            hours_left = max(
                0.0,
                (chargeback.respond_by - datetime.utcnow()).total_seconds() / 3600,
            )
        data["chargeback"] = {
            "id": chargeback.id,
            "payment_id": chargeback.payment_id,
            "amount_paise": chargeback.amount_paise,
            "reason_code": chargeback.reason_code,
            "reason_description": chargeback.reason_description,
            "status": chargeback.status,
            "phase": chargeback.phase,
            "respond_by": chargeback.respond_by.isoformat() if chargeback.respond_by else None,
            "evidence_submitted": chargeback.evidence_submitted,
            "hours_until_deadline": round(hours_left, 1) if hours_left is not None else None,
        }

    if audit_logs:
        data["audit_log"] = [
            {
                "id": a.id,
                "action": a.action,
                "actor_type": a.actor_type,
                "actor_id": a.actor_id,
                "reasoning": a.reasoning,
                "created_at": a.created_at,
            }
            for a in audit_logs
        ]

    return data


@router.get("")
async def list_cases(
    status: str = "open",
    page: int = 1,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * limit

    total_result = await db.execute(
        select(func.count()).select_from(ReconCase).where(ReconCase.status == status)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(ReconCase)
        .where(ReconCase.status == status)
        .order_by(desc(ReconCase.priority_score), desc(ReconCase.created_at))
        .offset(offset)
        .limit(limit)
    )
    cases = result.scalars().all()
    pages = math.ceil(total / limit) if total > 0 else 1

    return {
        "items": [
            {
                "id": c.id,
                "case_type": c.case_type,
                "merchant_id": c.merchant_id,
                "discrepancy_paise": c.discrepancy_paise,
                "priority_score": c.priority_score,
                "status": c.status,
                "ai_confidence": c.ai_confidence,
                "payment_id": c.payment_id,
                "settlement_id": c.settlement_id,
                "chargeback_id": c.chargeback_id,
                "created_at": c.created_at,
                "updated_at": c.updated_at,
            }
            for c in cases
        ],
        "total": total,
        "page": page,
        "pages": pages,
    }


@router.get("/{case_id}")
async def get_case(case_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    payment = None
    if case.payment_id:
        pay_result = await db.execute(
            select(PaymentEvent).where(PaymentEvent.id == case.payment_id)
        )
        payment = pay_result.scalars().first()

    chargeback = None
    if case.chargeback_id:
        cb_result = await db.execute(
            select(Chargeback).where(Chargeback.id == case.chargeback_id)
        )
        chargeback = cb_result.scalars().first()

    log_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_id == str(case_id), AuditLog.entity_type == "case")
        .order_by(desc(AuditLog.created_at))
        .limit(10)
    )
    audit_logs = log_result.scalars().all()

    return _case_to_detail(case, payment, chargeback, audit_logs)


@router.post("/{case_id}/analyze")
async def run_analysis(case_id: int, db: AsyncSession = Depends(get_db)):
    if not settings.has_ai_key:
        raise HTTPException(
            status_code=400,
            detail="No AI provider configured. Set GEMINI_API_KEY or ANTHROPIC_API_KEY in backend/.env",
        )

    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    agent_result = await analyze_case(case_id, db)

    if agent_result.error:
        raise HTTPException(status_code=500, detail=agent_result.error)

    # Re-fetch updated case
    return await get_case(case_id, db)


@router.post("/{case_id}/approve")
async def approve_case(
    case_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    note = body.get("note", "")
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = "manually_resolved"
    case.resolution_note = note
    case.updated_at = datetime.utcnow()

    audit = AuditLog(
        entity_type="case",
        entity_id=str(case_id),
        action="approved",
        actor_type="human",
        reasoning=note,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    await db.flush()

    return await get_case(case_id, db)


@router.post("/{case_id}/reject")
async def reject_case(
    case_id: int,
    body: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    reason = body.get("reason", "")
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.status = "open"
    case.ai_root_cause = None
    case.ai_resolution_steps = None
    case.ai_confidence = None
    case.updated_at = datetime.utcnow()

    audit = AuditLog(
        entity_type="case",
        entity_id=str(case_id),
        action="rejected",
        actor_type="human",
        reasoning=reason,
        created_at=datetime.utcnow(),
    )
    db.add(audit)
    await db.flush()

    return await get_case(case_id, db)
