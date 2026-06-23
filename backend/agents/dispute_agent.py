"""
Dispute agent — analyzes chargeback risk cases with deadline awareness.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.case import ReconCase, AuditLog
from models.chargeback import Chargeback
from agents.base import run_agent, AgentResult


DISPUTE_SYSTEM_PROMPT = """You are a chargeback specialist at a payments company.
A dispute requires a response before its deadline.
Use tools to fetch full chargeback and payment details.
The hours_until_deadline in the case context is critical — if under 48h, prioritize speed.

Respond in this exact format — no deviations:

ROOT CAUSE: <why the customer likely filed this dispute>
WIN PROBABILITY: <number 0.0-1.0>
EVIDENCE NEEDED:
- <specific document or record>
- <specific document or record>
RESOLUTION STEPS:
1. <action with deadline awareness>
2. <action>
3. <action>
confidence: <number between 0.0 and 1.0>"""


async def analyze_dispute_case(case_id: int, db: AsyncSession) -> AgentResult:
    # Fetch case
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        return AgentResult(text="", error=f"Case {case_id} not found", confidence=0.0)

    # Fetch chargeback
    chargeback = None
    hours_until_deadline = None
    if case.chargeback_id:
        cb_result = await db.execute(
            select(Chargeback).where(Chargeback.id == case.chargeback_id)
        )
        chargeback = cb_result.scalars().first()
        if chargeback and chargeback.respond_by:
            hours_until_deadline = max(
                0.0,
                (chargeback.respond_by - datetime.utcnow()).total_seconds() / 3600,
            )

    user_message = (
        f"Case ID: {case_id}\n"
        f"Type: {case.case_type}\n"
        f"Payment ID: {case.payment_id}\n"
        f"Chargeback ID: {case.chargeback_id}\n"
        f"Merchant: {case.merchant_id}\n"
        f"Amount: {case.discrepancy_paise} paise\n"
        f"Hours Until Deadline: {round(hours_until_deadline, 1) if hours_until_deadline is not None else 'unknown'}\n"
        f"Reason: {chargeback.reason_description if chargeback else 'N/A'}\n"
        f"Reason Code: {chargeback.reason_code if chargeback else 'N/A'}"
    )

    agent_result = await run_agent(DISPUTE_SYSTEM_PROMPT, user_message, db)

    if not agent_result.error:
        text = agent_result.text
        root_cause = ""
        resolution_steps = ""

        lines = text.split("\n")
        in_steps = False
        steps = []
        for line in lines:
            if line.startswith("ROOT CAUSE:"):
                root_cause = line.replace("ROOT CAUSE:", "").strip()
            elif line.startswith("RESOLUTION STEPS:"):
                in_steps = True
            elif in_steps and line.strip() and not line.lower().startswith("confidence"):
                steps.append(line.strip())
            elif line.lower().startswith("confidence"):
                in_steps = False

        resolution_steps = "\n".join(steps) if steps else text

        # Critical deadline prefix
        if hours_until_deadline is not None and hours_until_deadline < 24:
            root_cause = f"⚠️ DEADLINE CRITICAL: {root_cause}"

        case.ai_root_cause = root_cause or text[:500]
        case.ai_resolution_steps = resolution_steps
        case.ai_confidence = agent_result.confidence
        case.status = "pending_approval"
        case.updated_at = datetime.utcnow()

        # Insert audit log
        audit = AuditLog(
            entity_type="case",
            entity_id=str(case_id),
            action="agent_analyzed",
            actor_type="agent",
            actor_id="dispute_agent",
            reasoning=agent_result.text[:500],
            created_at=datetime.utcnow(),
        )
        db.add(audit)
        await db.flush()

    return agent_result
