# app/models/order.py

from sqlalchemy import Column, Integer, String, Text
from app.utils.database import Base

class Order(Base):
    __tablename__ = "order"

    id = Column(Integer, primary_key=True, index=True)  # автоинкремент

    date     = Column(String, nullable=True)                # Дата
    customer = Column(String, nullable=True)                # Покупатель
    phone    = Column(String, nullable=True)                # Телефон
    products = Column(Text, nullable=True)                  # Товары (список / строка)
    sum      = Column(String, nullable=True)                # Сумма
    status   = Column(String, nullable=True)                # Статус
    payment  = Column(String, nullable=True)                # Способ оплаты
    delivery = Column(String, nullable=True)                # Доставка
    track    = Column(String, nullable=True)                # Трек-номер
