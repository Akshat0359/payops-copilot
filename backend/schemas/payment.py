from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    order_id: str
    merchant_id: str
    amount_paise: int
    currency: str
    status: str
    method: Optional[str] = None
    bank: Optional[str] = None
    error_code: Optional[str] = None
    fee_paise: Optional[int] = None
    captured_at: Optional[datetime] = None
    created_at: datetime
