from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class Chargeback(Base):
    __tablename__ = "chargebacks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    payment_id: Mapped[str] = mapped_column(
        String, ForeignKey("payment_events.id"), nullable=False
    )
    amount_paise: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reason_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    phase: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    respond_by: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    evidence_submitted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
