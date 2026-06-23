"""
Bank statement CSV ingestion router.
"""
import csv
import io
from datetime import date, datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models.bank_entry import BankStatementEntry
from engine.matcher import run_matching_checks

router = APIRouter(prefix="/ingest", tags=["ingest"])

REQUIRED_COLUMNS = {"date", "narration", "debit", "credit", "balance", "utr"}


@router.post("/bank-statement")
async def ingest_bank_statement(
    file: UploadFile = File(...),
    account_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    text = content.decode("utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    # Validate columns
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty CSV file")

    fieldnames_lower = {f.strip().lower() for f in reader.fieldnames}
    missing = REQUIRED_COLUMNS - fieldnames_lower
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required CSV columns: {missing}",
        )

    rows_inserted = 0
    rows_skipped = 0
    new_utrs = []

    for row in reader:
        # Normalize keys
        row = {k.strip().lower(): v.strip() for k, v in row.items()}

        try:
            debit = int(float(row.get("debit") or "0") * 100)
        except ValueError:
            debit = 0
        try:
            credit = int(float(row.get("credit") or "0") * 100)
        except ValueError:
            credit = 0

        if debit == 0 and credit == 0:
            rows_skipped += 1
            continue

        if credit > 0:
            direction = "credit"
            amount_paise = credit
        else:
            direction = "debit"
            amount_paise = debit

        utr = row.get("utr") or None
        narration = row.get("narration") or None

        try:
            txn_date = date.fromisoformat(row.get("date", ""))
        except ValueError:
            try:
                from datetime import datetime as dt
                txn_date = dt.strptime(row.get("date", ""), "%d/%m/%Y").date()
            except ValueError:
                rows_skipped += 1
                continue

        entry = BankStatementEntry(
            account_id=account_id,
            utr=utr,
            narration=narration,
            amount_paise=amount_paise,
            direction=direction,
            transaction_date=txn_date,
        )
        db.add(entry)
        rows_inserted += 1
        if utr:
            new_utrs.append(utr)

    await db.flush()

    # Run matching for each new UTR
    for utr in new_utrs:
        await run_matching_checks(db, context_id=utr)

    return {"rows_inserted": rows_inserted, "rows_skipped": rows_skipped}
