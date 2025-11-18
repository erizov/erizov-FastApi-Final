# app/routes/lead.py

from fastapi import APIRouter, Depends, Request, status
from typing import List
from app.schemas.lead import Lead, LeadCreate, LeadBase, LeadIdResponse
from app.services.profile import (
    create_lead_service,
    read_leads_service,
    read_lead_service,
    update_lead_service,
    delete_lead_service,
)
from app.routes.auth import get_current_user

router = APIRouter()

# ────────────── CREATE ──────────────
@router.post(
    "/",
    response_model=LeadIdResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создать лид",
    response_description="Возвращает ID созданного лида",
    responses={
        201: {"description": "Лид успешно создан"},
        401: {"description": "Некорректный пользователь или токен"},
        409: {"description": "Нарушена уникальность ресурса"},
        422: {"description": "Неверные данные запроса"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def create_lead(
    request: Request,
    lead: LeadCreate,
    _: str = Depends(get_current_user),
):
    try:
        db_lead = await create_lead_service(lead, request)
        return {"id": db_lead.id}
    except Exception as e:
        await request.app.state.log.log_error("lead", f"Ошибка при создании лида: {str(e)}")
        raise

# ────────────── READ ALL ──────────────
@router.get(
    "/",
    response_model=List[Lead],
    status_code=status.HTTP_200_OK,
    summary="Получить список лидов",
    response_description="Возвращает список всех лидов",
    responses={
        200: {"description": "Список лидов успешно получен"},
        401: {"description": "Некорректный пользователь или токен"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def read_leads(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    _: str = Depends(get_current_user),
):
    try:
        leads = await read_leads_service(request, skip, limit)
        await request.app.state.log.log_info("lead", "Список лидов загружен", {"count": len(leads)})
        return leads
    except Exception as e:
        await request.app.state.log.log_error("lead", f"Ошибка при получении списка лидов: {str(e)}")
        raise

# ────────────── READ ONE ──────────────
@router.get(
    "/{id}",
    response_model=Lead,
    status_code=status.HTTP_200_OK,
    summary="Получить лид по ID",
    response_description="Возвращает данные конкретного лида",
    responses={
        200: {"description": "Лид найден и возвращён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Лид не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def read_lead(
    id: int,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        lead = await read_lead_service(id, request)
        return lead
    except Exception as e:
        await request.app.state.log.log_error("lead", f"Ошибка при получении лида: {str(e)}", {"id": id})
        raise

# ────────────── UPDATE ──────────────
@router.put(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Обновить лид",
    response_description="Лид успешно обновлён",
    responses={
        200: {"description": "Лид успешно обновлён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Лид не найден"},
        422: {"description": "Неверные данные запроса"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def update_lead(
    id: int,
    lead_update: LeadBase,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        updated_lead = await update_lead_service(id, lead_update, request)
        return updated_lead
    except Exception as e:
        await request.app.state.log.log_error("lead", f"Ошибка при обновлении лида: {str(e)}", {"id": id})
        raise

# ────────────── DELETE ──────────────
@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить лид",
    response_description="Лид успешно удалён, тело ответа отсутствует",
    responses={
        204: {"description": "Лид успешно удалён"},
        401: {"description": "Некорректный пользователь или токен"},
        404: {"description": "Лид не найден"},
        500: {"description": "Внутренняя ошибка сервера"},
    },
)
async def delete_lead(
    id: int,
    request: Request,
    _: str = Depends(get_current_user),
):
    try:
        await delete_lead_service(id, request)
    except Exception as e:
        await request.app.state.log.log_error("lead", f"Ошибка при удалении лида: {str(e)}", {"id": id})
        raise
