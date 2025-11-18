# app/schemas/user.py

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """
    Базовая схема пользователя для входных данных и обновления.
    """
    name: Optional[str] = None
    login: Optional[str] = None
    password: Optional[str] = None  
    is_admin: Optional[bool] = False

class UserCreate(UserBase):
    """
    Схема для создания нового пользователя.
    Все поля необязательные, можно указать name, login и password.
    """
    pass

class UserUpdate(UserBase):
    """
    Схема для обновления пользователя.
    Передаются только те поля, которые нужно изменить.
    """
    pass

class UserResponse(UserBase):
    """
    Схема для ответа API при чтении пользователя
    """
    id: int
    timestamp: datetime

    model_config = {
        "from_attributes": True
    }
