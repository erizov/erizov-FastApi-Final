# app/schemas/lead.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# ────────────── Базовая схема ──────────────
class LeadBase(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    log: Optional[str] = None       # JSON-храним как текст

# ────────────── Схема для CREATE ──────────────
class LeadCreate(LeadBase):
    pass  # все поля необязательные, можно наследовать без изменений

class LeadIdResponse(BaseModel):
    id: int

# ────────────── Схема для RESPONSE ──────────────
class Lead(LeadBase):
    id: int
    timestamp: datetime

    model_config = {
        "from_attributes": True
    }
