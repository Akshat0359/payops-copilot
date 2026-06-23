"""
Seed script — populates the database with realistic demo data.
Run from backend/ directory: python seeds/seed.py
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta, date

# Ensure backend/ is on PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, AsyncSessionLocal
from models.payment import PaymentEvent
from models.settlement import Settlement, SettlementPayment
from models.refund import Refund
from models.chargeback import Chargeback
from models.bank_entry import BankStatementEntry
from engine.matcher import run_matching_checks
from engine.priority_scorer import compute_priority_score


def _net(amount_paise: int, fee_pct: float = 2.0) -> int:
    fee = amount_paise * fee_pct / 100
    gst = fee * 0.18
    return int(amount_paise - fee - gst)


async def main():
    await init_db()

    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        five_days_ago = now - timedelta(days=5)
        four_days_ago = now - timedelta(days=4)
        one_day_ago = now - timedelta(days=1)
        two_days_ago = now - timedelta(days=2)

        # ── PAYMENTS ─────────────────────────────────────────────────
        amounts = [
            500_00, 1200_00, 3400_00, 750_00, 15000_00,
            8900_00, 450_00, 22000_00, 5600_00, 3100_00,
            9800_00, 1500_00, 47000_00, 2300_00, 6700_00,
        ]
        methods = ["upi", "card", "netbanking"]
        payments = []

        for i, amount in enumerate(amounts, start=1):
            pid = f"pay_{i:03d}"
            if i <= 10:
                created = five_days_ago
            elif i <= 13:
                created = four_days_ago
            else:
                created = one_day_ago

            p = PaymentEvent(
                id=pid,
                order_id=f"order_{i:03d}",
                merchant_id="merchant_001",
                amount_paise=amount,
                currency="INR",
                status="captured",
                method=methods[(i - 1) % 3],
                created_at=created,
            )
            db.add(p)
            payments.append(p)

        await db.flush()
        print(f"  Inserted {len(payments)} payments")

        # ── SETTLEMENTS (skip pay_004 and pay_009) ────────────────────
        skip_payments = {"pay_004", "pay_009"}
        settlements = []
        settlement_count = 0

        for i, payment in enumerate(payments, start=1):
            if payment.id in skip_payments:
                continue

            settlement_count += 1
            sid = f"S{settlement_count:03d}"
            net = _net(payment.amount_paise)

            s = Settlement(
                id=sid,
                merchant_id="merchant_001",
                amount_paise=net,
                fees_paise=int(payment.amount_paise * 0.02 * 1.18),
                utr=f"UTR{sid}",
                status="processed",
                settled_at=two_days_ago,
                created_at=two_days_ago,
            )
            db.add(s)

            sp = SettlementPayment(
                settlement_id=sid,
                payment_id=payment.id,
                amount_paise=net,
            )
            db.add(sp)
            settlements.append((payment, s))

        await db.flush()
        print(f"  Inserted {settlement_count} settlements")

        # ── BANK ENTRIES ─────────────────────────────────────────────
        txn_date = (now - timedelta(days=2)).date()
        bank_count = 0

        for i, (payment, settlement) in enumerate(settlements, start=1):
            # Entry for pay_006 (index 5 in settlements, payment pay_006) has wrong amount
            if payment.id == "pay_006":
                amount = settlement.amount_paise + 15000  # ₹150 discrepancy
            else:
                amount = settlement.amount_paise

            entry = BankStatementEntry(
                account_id="HDFC_001",
                utr=settlement.utr,
                narration=f"NEFT/{settlement.utr}/Settlement",
                amount_paise=amount,
                direction="credit",
                transaction_date=txn_date,
            )
            db.add(entry)
            bank_count += 1

        await db.flush()
        print(f"  Inserted {bank_count} bank entries")

        # ── REFUNDS ───────────────────────────────────────────────────
        refunds = [
            Refund(
                id="refund_001",
                payment_id="pay_002",
                amount_paise=1200_00,
                status="processed",
                created_at=now - timedelta(days=3),
            ),
            Refund(
                id="refund_002",
                payment_id="pay_011",
                amount_paise=1500_00,
                status="processed",
                created_at=now - timedelta(days=2),
            ),
            Refund(
                id="refund_003",
                payment_id="pay_011",
                amount_paise=1500_00,
                status="processed",
                created_at=now - timedelta(days=1),
            ),
        ]
        for r in refunds:
            db.add(r)
        await db.flush()
        print(f"  Inserted {len(refunds)} refunds (refund_002 + refund_003 are duplicates)")

        # ── CHARGEBACKS ───────────────────────────────────────────────
        chargebacks = [
            Chargeback(
                id="chargeback_001",
                payment_id="pay_005",
                amount_paise=15000_00,
                reason_code="RD",
                reason_description="Customer claims non-delivery",
                status="open",
                phase="chargeback",
                respond_by=now + timedelta(hours=20),  # CRITICAL
                evidence_submitted=False,
                created_at=now - timedelta(days=1),
            ),
            Chargeback(
                id="chargeback_002",
                payment_id="pay_008",
                amount_paise=22000_00,
                reason_code="UA",
                reason_description="Unauthorized transaction claim",
                status="open",
                phase="chargeback",
                respond_by=now + timedelta(hours=120),  # 5 days
                evidence_submitted=False,
                created_at=now - timedelta(days=2),
            ),
        ]
        for cb in chargebacks:
            db.add(cb)
        await db.flush()
        print(f"  Inserted {len(chargebacks)} chargebacks")

        # ── RUN MATCHING ──────────────────────────────────────────────
        new_cases = await run_matching_checks(db)
        await db.commit()
        print(f"\nSeed complete. Cases created: {len(new_cases)}")
        for case in new_cases:
            print(f"  [{case.case_type}] id={case.id} priority={case.priority_score}")


if __name__ == "__main__":
    asyncio.run(main())
