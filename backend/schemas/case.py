from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    actor_type: str
    actor_id: Optional[str] = None
    reasoning: Optional[str] = None
    created_at: datetime


class CaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    case_type: str
    merchant_id: str
    discrepancy_paise: Optional[int] = None
    priority_score: int
    status: str
    ai_confidence: Optional[float] = None
    payment_id: Optional[str] = None
    settlement_id: Optional[str] = None
    chargeback_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class CaseDetail(CaseOut):
    ai_root_cause: Optional[str] = None
    ai_resolution_steps: Optional[str] = None
    payment: Optional[dict] = None
    chargeback: Optional[dict] = None
    audit_log: list[AuditLogOut] = []
