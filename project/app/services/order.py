# app/services/order.py

from sqlalchemy.future import select
from fastapi import HTTPException, Request

from app.models.order import Order as OrderModel
from app.schemas.order import OrderCreate, OrderBase


async def read_orders_service(request: Request, skip: int = 0, limit: int = 100) -> list[OrderModel]:
    """
    Получение списка заказов
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(OrderModel).offset(skip).limit(limit))
    orders = result.scalars().all()

    await log.log_info("order", f"{len(orders)} заказов загружено")
    return orders


async def create_order_service(order: OrderCreate, request: Request) -> OrderModel:
    """
    Создание нового заказа.
    """
    db = request.state.db
    log = request.app.state.log

    db_order = OrderModel(**order.dict())
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    await log.log_info("order", "Заказ создан", {"id": db_order.id})
    return db_order


async def read_order_service(id: int, request: Request) -> OrderModel:
    """
    Чтение заказа по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(OrderModel).where(OrderModel.id == id))
    db_order = result.scalar_one_or_none()
    if db_order is None:
        await log.log_error("order", "Заказ не найден", {"id": id})
        raise HTTPException(status_code=404, detail="Заказ не найден")

    await log.log_info("order", "Заказ загружен", {"id": id})
    return db_order


async def update_order_service(id: int, order_update: OrderBase, request: Request) -> OrderModel:
    """
    Обновление заказа по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(OrderModel).where(OrderModel.id == id))
    db_order = result.scalar_one_or_none()
    if db_order is None:
        await log.log_error("order", "Заказ не найден для обновления", {"id": id})
        raise HTTPException(status_code=404, detail="Заказ не найден")

    for key, value in order_update.dict(exclude_unset=True).items():
        setattr(db_order, key, value)

    db.add(db_order)
    await db.commit()
    await log.log_info("order", "Заказ обновлён", {"id": id})
    return db_order


async def delete_order_service(id: int, request: Request) -> None:
    """
    Удаление заказа по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(OrderModel).where(OrderModel.id == id))
    db_order = result.scalar_one_or_none()
    if db_order is None:
        await log.log_error("order", "Заказ не найден для удаления", {"id": id})
        raise HTTPException(status_code=404, detail="Заказ не найден")

    await db.delete(db_order)
    await db.commit()
    await log.log_info("order", "Заказ удалён", {"id": id})
