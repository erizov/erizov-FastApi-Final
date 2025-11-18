# app/schemas/order.py

from pydantic import BaseModel
from typing import Optional

class OrderBase(BaseModel):
    date: Optional[str] = None
    customer: Optional[str] = None
    phone: Optional[str] = None
    products: Optional[str] = None
    sum: Optional[str] = None
    status: Optional[str] = None
    payment: Optional[str] = None
    delivery: Optional[str] = None
    track: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    id: int

    class Config:
        orm_mode = True
