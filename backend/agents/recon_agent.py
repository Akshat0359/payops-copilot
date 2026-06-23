"""
Reconciliation agent — analyzes settlement mismatches, missing settlements, and duplicate refunds.
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.case import ReconCase, AuditLog
from models.payment import PaymentEvent
from agents.base import run_agent, AgentResult


RECON_SYSTEM_PROMPT = """You are a reconciliation specialist at a payments company.
A settlement mismatch or missing settlement has been flagged.
Use the available tools to fetch payment, settlement, and bank entry details.
Compare amounts using compute_expected_settlement to know what the merchant should receive.
Check get_similar_cases to see if this pattern has occurred before.

Respond in this exact format — no deviations:

ROOT CAUSE: <one clear sentence>
RESOLUTION STEPS:
1. <concrete action with specific IDs>
2. <concrete action>
3. <concrete action>
confidence: <number between 0.0 and 1.0>"""


async def analyze_recon_case(case_id: int, db: AsyncSession) -> AgentResult:
    # Fetch case
    result = await db.execute(select(ReconCase).where(ReconCase.id == case_id))
    case = result.scalars().first()
    if not case:
        return AgentResult(text="", error=f"Case {case_id} not found", confidence=0.0)

    # Fetch payment details if available
    payment_info = ""
    if case.payment_id:
        pay_result = await db.execute(
            select(PaymentEvent).where(PaymentEvent.id == case.payment_id)
        )
        payment = pay_result.scalars().first()
        if payment:
            payment_info = (
                f"\nPayment Amount: {payment.amount_paise} paise"
                f"\nPayment Method: {payment.method}"
                f"\nPayment Status: {payment.status}"
            )

    user_message = (
        f"Case ID: {case_id}\n"
        f"Type: {case.case_type}\n"
        f"Payment ID: {case.payment_id}\n"
        f"Merchant: {case.merchant_id}\n"
        f"Discrepancy: {case.discrepancy_paise} paise\n"
        f"Created: {case.created_at}"
        f"{payment_info}"
    )

    agent_result = await run_agent(RECON_SYSTEM_PROMPT, user_message, db)

    if not agent_result.error:
        # Parse root cause and resolution steps from the structured response
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
            actor_id="recon_agent",
            reasoning=agent_result.text[:500],
            created_at=datetime.utcnow(),
        )
        db.add(audit)
        await db.flush()

    return agent_result
