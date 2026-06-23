from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class ReconCase(Base):
    __tablename__ = "recon_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_type: Mapped[str] = mapped_column(String, nullable=False)
    payment_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    settlement_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    chargeback_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    merchant_id: Mapped[str] = mapped_column(String, nullable=False)
    discrepancy_paise: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    priority_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String, default="open", nullable=False)
    ai_root_cause: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_resolution_steps: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ai_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    assigned_to: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    resolution_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)
    actor_type: Mapped[str] = mapped_column(String, nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    reasoning: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
