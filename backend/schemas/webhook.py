from typing import Optional, Any
from pydantic import BaseModel


class PaymentEntity(BaseModel):
    id: str
    order_id: Optional[str] = ""
    merchant_id: Optional[str] = "unknown"
    amount: Optional[int] = 0
    currency: Optional[str] = "INR"
    status: Optional[str] = "captured"
    method: Optional[str] = None
    bank: Optional[str] = None
    fee: Optional[int] = None
    created_at: Optional[int] = None


class RefundEntity(BaseModel):
    id: str
    payment_id: str
    amount: Optional[int] = 0
    status: Optional[str] = "processed"
    speed_requested: Optional[str] = None
    created_at: Optional[int] = None


class SettlementEntity(BaseModel):
    id: str
    merchant_id: Optional[str] = "unknown"
    amount: Optional[int] = 0
    fees: Optional[int] = None
    utr: Optional[str] = None
    status: Optional[str] = "processed"
    created_at: Optional[int] = None


class DisputeEntity(BaseModel):
    id: str
    payment_id: str
    amount: Optional[int] = 0
    reason_code: Optional[str] = None
    reason_description: Optional[str] = None
    status: Optional[str] = "open"
    phase: Optional[str] = None


class PaymentWrapper(BaseModel):
    entity: PaymentEntity


class RefundWrapper(BaseModel):
    entity: RefundEntity


class SettlementWrapper(BaseModel):
    entity: SettlementEntity


class DisputeWrapper(BaseModel):
    entity: DisputeEntity


class WebhookPayload(BaseModel):
    payment: Optional[PaymentWrapper] = None
    refund: Optional[RefundWrapper] = None
    settlement: Optional[SettlementWrapper] = None
    dispute: Optional[DisputeWrapper] = None


class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: WebhookPayload
