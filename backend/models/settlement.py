from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String, nullable=False)
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    fees_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    utr: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )


class SettlementPayment(Base):
    __tablename__ = "settlement_payments"
    __table_args__ = (
        UniqueConstraint("settlement_id", "payment_id", name="uq_settlement_payment"),
    )

    settlement_id: Mapped[str] = mapped_column(
        String, ForeignKey("settlements.id"), primary_key=True
    )
    payment_id: Mapped[str] = mapped_column(
        String, ForeignKey("payment_events.id"), primary_key=True
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
