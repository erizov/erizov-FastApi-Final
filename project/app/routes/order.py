# app/routes/order.py

from fastapi import APIRouter, Depends, Request, status
from typing import List
from app.schemas.order import Order, OrderCreate, OrderBase
from app.services.order import (
    create_order_service,
    read_orders_service,
    read_order_service,
    update_order_service,
    delete_order_service,
)
from app.routes.auth import get_current_user

router = APIRouter()

# ────────────── CREATE ──────────────
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    summary="Создать заказ",
    response_description="Возвращает ID созданного заказа",
    responses={
        201: {"description": "Заказ успешно создан"},
        401: {"description": "Некорректный пользователь или токен"},
        409: {"description": "Нарушена уникальность ресурса"},
        422: {"description": "Неверные данные запроса"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create_order(
    request: Request,
    order: OrderCreate,
    _: str = Depends(get_current_user),
):
    try:
        db_order = await create_order_service(order, request)
        return {"id": db_order.id}
    except Exception as e:
        await request.app.state.log.log_error("order", f"Ошибка при создании заказа: {str(e)}")
        raise


# ────────────── READ ALL ──────────────
@router.get(
    "/",
    response_model=List[Order],
    status_code=status.HTTP_200_OK,
    summary="Получить список заказов",
    response_description="Возвращает список всех заказов",
    responses={
        200: {"description": "Список заказов успешно получен"},
        401: {"description": "Некорректный пользователь или токен"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def read_orders(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    _: str = Depends(get_current_user),
):
    try:
        orders = await read_orders_service(request, skip, limit)
        await request.app.state.log.log_info("order", "Список заказов загружен", {"count": len(orders)})
        return orders
    except Exception as e:
        await request.app.state.log.log_error("order", f"Ошибка при получении списка заказов: {str(e)}")
        raise


# ────────────── READ ONE ──────────────
@router.get(
    "/{id}",
    response_model=Order,
    status_code=status.HTTP_200_OK,
    summary="Получить заказ по ID",
    response_description="Возвращает данные конкретного заказа",
    responses={
        200: {"description": "Заказ найден и возвращён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Заказ не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def read_order(
    id: int,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        order = await read_order_service(id, request)
        return order
    except Exception as e:
        await request.app.state.log.log_error("order", f"Ошибка при получении заказа: {str(e)}", {"id": id})
        raise


# ────────────── UPDATE ──────────────
@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Обновить заказ",
    response_description="Заказ успешно обновлён",
    responses={
        200: {"description": "Заказ успешно обновлён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Заказ не найден"},
        422: {"description": "Неверные данные запроса"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def update_order(
    id: int,
    order_update: OrderBase,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        updated_order = await update_order_service(id, order_update, request)
        return updated_order
    except Exception as e:
        await request.app.state.log.log_error("order", f"Ошибка при обновлении заказа: {str(e)}", {"id": id})
        raise


# ────────────── DELETE ──────────────
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить заказ",
    response_description="Заказ успешно удалён, тело ответа отсутствует",
    responses={
        204: {"description": "Заказ успешно удалён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Заказ не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def delete_order(
    id: int,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        await delete_order_service(id, request)
    except Exception as e:
        await request.app.state.log.log_error("order", f"Ошибка при удалении заказа: {str(e)}", {"id": id})
        raise
