# app/models/lead.py

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.utils.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)  # автоинкремент
    name = Column(String, nullable=True)
    contact = Column(String, nullable=True)
    log = Column(Text, nullable=True)       # JSON-храним как текст   
    login = Column(String, unique=True, nullable=True)  # логин
    password = Column(String, nullable=True)            # пароль
    is_admin = Column(Boolean, default=False)           # флаг админа   
    timestamp = Column(DateTime(timezone=True), server_default=func.now())    
