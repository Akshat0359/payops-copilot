"""
Analytics router — dashboard metrics.
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models.case import ReconCase
from models.chargeback import Chargeback

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Open cases
    open_result = await db.execute(
        select(func.count()).select_from(ReconCase).where(ReconCase.status == "open")
    )
    open_cases = open_result.scalar_one()

    # Pending approval
    pending_result = await db.execute(
        select(func.count())
        .select_from(ReconCase)
        .where(ReconCase.status == "pending_approval")
    )
    pending_approval = pending_result.scalar_one()

    # Auto-resolved today
    auto_result = await db.execute(
        select(func.count())
        .select_from(ReconCase)
        .where(
            ReconCase.status == "auto_resolved",
            ReconCase.updated_at >= today_start,
        )
    )
    auto_resolved_today = auto_result.scalar_one()

    # Manually resolved today
    manual_result = await db.execute(
        select(func.count())
        .select_from(ReconCase)
        .where(
            ReconCase.status == "manually_resolved",
            ReconCase.updated_at >= today_start,
        )
    )
    manually_resolved_today = manual_result.scalar_one()

    # Disputes due in 24h
    deadline_threshold = now + timedelta(hours=24)
    disputes_result = await db.execute(
        select(func.count())
        .select_from(Chargeback)
        .where(
            Chargeback.status == "open",
            Chargeback.respond_by <= deadline_threshold,
        )
    )
    disputes_due_24h = disputes_result.scalar_one()

    # Cases by type
    types = ["AMOUNT_MISMATCH", "MISSING_SETTLEMENT", "DUPLICATE_REFUND", "CHARGEBACK_RISK"]
    cases_by_type = {}
    for case_type in types:
        type_result = await db.execute(
            select(func.count())
            .select_from(ReconCase)
            .where(ReconCase.case_type == case_type)
        )
        cases_by_type[case_type] = type_result.scalar_one()

    # Average confidence
    avg_result = await db.execute(
        select(func.avg(ReconCase.ai_confidence)).where(
            ReconCase.ai_confidence.is_not(None)
        )
    )
    avg_confidence = avg_result.scalar_one()

    return {
        "open_cases": open_cases,
        "pending_approval": pending_approval,
        "auto_resolved_today": auto_resolved_today,
        "manually_resolved_today": manually_resolved_today,
        "disputes_due_24h": disputes_due_24h,
        "cases_by_type": cases_by_type,
        "avg_confidence": round(avg_confidence, 3) if avg_confidence else None,
    }
