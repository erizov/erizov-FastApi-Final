# app/services/profile.py

from sqlalchemy.future import select
from fastapi import HTTPException, Request

from app.models.lead import Lead as LeadModel
from app.schemas.lead import LeadCreate, LeadBase


async def read_leads_service(request: Request, skip: int = 0, limit: int = 100) -> list[LeadModel]:
    """
    Получение списка лидов с логированием.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(LeadModel).offset(skip).limit(limit))
    leads = result.scalars().all()

    await log.log_info("lead", f"{len(leads)} лидов загружено")
    return leads


async def create_lead_service(lead: LeadCreate, request: Request) -> LeadModel:
    """
    Создание нового лида.
    """
    db = request.state.db
    log = request.app.state.log

    db_lead = LeadModel(**lead.dict())
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)

    await log.log_info("lead", "Лид создан", {"id": db_lead.id})
    return db_lead

async def read_lead_service(id: int, request: Request) -> LeadModel:
    """
    Чтение лида по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(LeadModel).where(LeadModel.id == id))
    db_lead = result.scalar_one_or_none()
    if db_lead is None:
        await log.log_error("lead", "Лид не найден", {"id": id})
        raise HTTPException(status_code=404, detail="Лид не найден")

    await log.log_info("lead", "Лид загружен", {"id": id})
    return db_lead


async def update_lead_service(id: int, lead_update: LeadBase, request: Request) -> LeadModel:
    """
    Обновление лида по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(LeadModel).where(LeadModel.id == id))
    db_lead = result.scalar_one_or_none()
    if db_lead is None:
        await log.log_error("lead", "Лид не найден для обновления", {"id": id})
        raise HTTPException(status_code=404, detail="Лид не найден")

    for key, value in lead_update.dict(exclude_unset=True).items():
        setattr(db_lead, key, value)

    db.add(db_lead)
    await db.commit()
    await log.log_info("lead", "Лид обновлён", {"id": id})
    return db_lead


async def delete_lead_service(id: int, request: Request) -> None:
    """
    Удаление лида по ID.
    """
    db = request.state.db
    log = request.app.state.log

    result = await db.execute(select(LeadModel).where(LeadModel.id == id))
    db_lead = result.scalar_one_or_none()
    if db_lead is None:
        await log.log_error("lead", "Лид не найден для удаления", {"id": id})
        raise HTTPException(status_code=404, detail="Лид не найден")

    await db.delete(db_lead)
    await db.commit()
    await log.log_info("lead", "Лид удалён", {"id": id})
