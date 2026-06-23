"""
Orchestrator — routes cases to the appropriate agent based on case_type.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.case import ReconCase
from agents.base import AgentResult
from agents import recon_agent, dispute_agent


async def analyze_case(case_id: int, db: AsyncSession) -> AgentResult:
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        return AgentResult(text="", error=f"Case {case_id} not found", confidence=0.0)

    if case.case_type == "CHARGEBACK_RISK":
        return await dispute_agent.analyze_dispute_case(case_id, db)
    else:
        return await recon_agent.analyze_recon_case(case_id, db)
