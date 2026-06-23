from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Date
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class BankStatementEntry(Base):
    __tablename__ = "bank_statement_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    utr: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    narration: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)  # "credit" or "debit"
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    matched_settlement_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    matched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
