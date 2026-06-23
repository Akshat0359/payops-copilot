"""
Tool definitions and dispatcher for Claude function-calling agents.
"""
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.payment import PaymentEvent
from models.settlement import Settlement, SettlementPayment
from models.chargeback import Chargeback
from models.bank_entry import BankStatementEntry
from models.case import ReconCase


# ─────────────────────────────────────────────
# PYTHON TOOL FUNCTIONS
# ─────────────────────────────────────────────

async def get_payment(db: AsyncSession, payment_id: str) -> dict:
    result = await db.execute(
        select(PaymentEvent).where(PaymentEvent.id == payment_id)
    )
    payment = result.scalars().first()
    if not payment:
        return {"error": "not found"}
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "merchant_id": payment.merchant_id,
        "amount_paise": payment.amount_paise,
        "currency": payment.currency,
        "status": payment.status,
        "method": payment.method,
        "bank": payment.bank,
        "error_code": payment.error_code,
        "fee_paise": payment.fee_paise,
        "captured_at": payment.captured_at.isoformat() if payment.captured_at else None,
        "created_at": payment.created_at.isoformat(),
    }


async def get_settlement_for_payment(db: AsyncSession, payment_id: str) -> dict:
    link_result = await db.execute(
        select(SettlementPayment).where(SettlementPayment.payment_id == payment_id)
    )
    link = link_result.scalars().first()
    if not link:
        return {"error": "no settlement found"}

    settle_result = await db.execute(
        select(Settlement).where(Settlement.id == link.settlement_id)
    )
    settlement = settle_result.scalars().first()
    if not settlement:
        return {"error": "no settlement found"}

    return {
        "id": settlement.id,
        "merchant_id": settlement.merchant_id,
        "amount_paise": settlement.amount_paise,
        "fees_paise": settlement.fees_paise,
        "utr": settlement.utr,
        "status": settlement.status,
        "settled_at": settlement.settled_at.isoformat() if settlement.settled_at else None,
        "created_at": settlement.created_at.isoformat(),
    }


async def get_chargeback(db: AsyncSession, chargeback_id: str) -> dict:
    result = await db.execute(
        select(Chargeback).where(Chargeback.id == chargeback_id)
    )
    cb = result.scalars().first()
    if not cb:
        return {"error": "not found"}

    hours_until_deadline = None
    if cb.respond_by:
        hours_until_deadline = max(
            0.0, (cb.respond_by - datetime.utcnow()).total_seconds() / 3600
        )

    return {
        "id": cb.id,
        "payment_id": cb.payment_id,
        "amount_paise": cb.amount_paise,
        "reason_code": cb.reason_code,
        "reason_description": cb.reason_description,
        "status": cb.status,
        "phase": cb.phase,
        "respond_by": cb.respond_by.isoformat() if cb.respond_by else None,
        "evidence_submitted": cb.evidence_submitted,
        "hours_until_deadline": round(hours_until_deadline, 1) if hours_until_deadline is not None else None,
        "created_at": cb.created_at.isoformat(),
    }


async def get_bank_entry_by_utr(db: AsyncSession, utr: str) -> dict:
    result = await db.execute(
        select(BankStatementEntry).where(BankStatementEntry.utr == utr)
    )
    entry = result.scalars().first()
    if not entry:
        return {"error": "not found"}
    return {
        "id": entry.id,
        "account_id": entry.account_id,
        "utr": entry.utr,
        "narration": entry.narration,
        "amount_paise": entry.amount_paise,
        "direction": entry.direction,
        "transaction_date": entry.transaction_date.isoformat(),
        "matched_settlement_id": entry.matched_settlement_id,
    }


async def get_similar_cases(
    db: AsyncSession, description: str, limit: int = 3
) -> list[dict]:
    # Extract first meaningful word (skip stop words)
    stop_words = {"the", "a", "an", "is", "in", "of", "for", "this", "that"}
    words = [w for w in description.lower().split() if w not in stop_words and len(w) > 3]
    keyword = words[0] if words else description[:10]

    result = await db.execute(
        select(ReconCase)
        .where(ReconCase.ai_root_cause.ilike(f"%{keyword}%"))
        .limit(limit)
    )
    cases = result.scalars().all()
    return [
        {
            "id": c.id,
            "case_type": c.case_type,
            "status": c.status,
            "ai_root_cause": c.ai_root_cause,
            "ai_confidence": c.ai_confidence,
        }
        for c in cases
    ]


def compute_expected_settlement(amount_paise: int, fee_pct: float = 2.0) -> dict:
    fee = amount_paise * fee_pct / 100
    gst = fee * 0.18
    net = amount_paise - fee - gst
    return {
        "gross_paise": amount_paise,
        "fee_paise": int(fee),
        "gst_paise": int(gst),
        "expected_net_paise": int(net),
    }


def draft_escalation_email(utr: str, amount_paise: int) -> str:
    amount_inr = amount_paise / 100
    return (
        f"Subject: Settlement Discrepancy - UTR {utr}\n\n"
        f"Dear Banking Team,\n\n"
        f"We have identified a discrepancy in settlement with UTR reference {utr}. "
        f"The expected credit of ₹{amount_inr:.2f} does not match our records.\n\n"
        f"Please investigate and provide a reconciliation statement at the earliest.\n\n"
        f"Regards,\nPayOps Team"
    )


# ─────────────────────────────────────────────
# TOOL SCHEMAS
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_payment",
        "description": "Fetch full details of a payment event by its payment ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "The Razorpay payment ID (e.g. pay_001)",
                }
            },
            "required": ["payment_id"],
        },
    },
    {
        "name": "get_settlement_for_payment",
        "description": "Fetch the settlement linked to a specific payment ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "payment_id": {
                    "type": "string",
                    "description": "The Razorpay payment ID",
                }
            },
            "required": ["payment_id"],
        },
    },
    {
        "name": "get_chargeback",
        "description": "Fetch chargeback details including hours until deadline.",
        "input_schema": {
            "type": "object",
            "properties": {
                "chargeback_id": {
                    "type": "string",
                    "description": "The chargeback ID",
                }
            },
            "required": ["chargeback_id"],
        },
    },
    {
        "name": "get_bank_entry_by_utr",
        "description": "Fetch a bank statement entry by its UTR reference number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "utr": {
                    "type": "string",
                    "description": "The UTR (Unique Transaction Reference) number",
                }
            },
            "required": ["utr"],
        },
    },
    {
        "name": "get_similar_cases",
        "description": "Find similar resolved cases based on a description keyword.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Description of the issue to search for similar cases",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of cases to return (default 3)",
                    "default": 3,
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "compute_expected_settlement",
        "description": "Calculate the expected net settlement amount after Razorpay fees and GST.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount_paise": {
                    "type": "integer",
                    "description": "Gross payment amount in paise (1 INR = 100 paise)",
                },
                "fee_pct": {
                    "type": "number",
                    "description": "Razorpay fee percentage (default 2.0)",
                    "default": 2.0,
                },
            },
            "required": ["amount_paise"],
        },
    },
    {
        "name": "draft_escalation_email",
        "description": "Generate a formatted escalation email to the banking team for a UTR discrepancy.",
        "input_schema": {
            "type": "object",
            "properties": {
                "utr": {
                    "type": "string",
                    "description": "The UTR reference number",
                },
                "amount_paise": {
                    "type": "integer",
                    "description": "The discrepant amount in paise",
                },
            },
            "required": ["utr", "amount_paise"],
        },
    },
]


# ─────────────────────────────────────────────
# TOOL DISPATCHER
# ─────────────────────────────────────────────

async def execute_tool(tool_name: str, tool_input: dict, db: AsyncSession) -> str:
    if tool_name == "get_payment":
        result = await get_payment(db, tool_input["payment_id"])
    elif tool_name == "get_settlement_for_payment":
        result = await get_settlement_for_payment(db, tool_input["payment_id"])
    elif tool_name == "get_chargeback":
        result = await get_chargeback(db, tool_input["chargeback_id"])
    elif tool_name == "get_bank_entry_by_utr":
        result = await get_bank_entry_by_utr(db, tool_input["utr"])
    elif tool_name == "get_similar_cases":
        result = await get_similar_cases(
            db, tool_input["description"], tool_input.get("limit", 3)
        )
    elif tool_name == "compute_expected_settlement":
        result = compute_expected_settlement(
            tool_input["amount_paise"], tool_input.get("fee_pct", 2.0)
        )
    elif tool_name == "draft_escalation_email":
        result = draft_escalation_email(tool_input["utr"], tool_input["amount_paise"])
    else:
        result = {"error": f"Unknown tool: {tool_name}"}

    return json.dumps(result, default=str)
