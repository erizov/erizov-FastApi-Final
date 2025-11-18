# app/routes/base.py

from fastapi import Request, HTTPException, Depends, APIRouter
from fastapi.responses import JSONResponse
from typing import Any, Dict, List
from app.schemas.base import ChunkSearchRequest
from app.services.base import Base
from app.services.gpt import ask
from app.routes.auth import get_current_user
from pydantic import BaseModel

router = APIRouter()


@router.get(
    "/document",
    summary="Загрузить локальный документ",
    responses={
        200: {"description": "Документ успешно загружен", "content": {"application/json": {"example": {"text": "Содержимое документа..."}}}},
        404: {"description": "Файл документа не найден"},
        500: {"description": "Ошибка обработки документа на сервере"},
    },
)
async def get_document(request: Request, _: str = Depends(get_current_user)):
    base: Base = request.app.state.base
    log = request.app.state.log

    try:
        text = base.load_local_document()
        await log.log_info("base", f"Документ загружен, длина текста {len(text)}")
        return {"text": text}
    except FileNotFoundError as e:
        await log.log_error("base", f"Документ не найден: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log.log_error("base", f"Ошибка загрузки документа: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(e)}")


@router.post(
    "/chunks",
    summary="Поиск релевантных чанков",
    responses={
        200: {"description": "Список релевантных чанков найден", "content": {"application/json": {"example": {"results": [{"content": "Текст чанка...", "metadata": {"page": 1}, "score": 0.123}]}}}},
        400: {"description": "Параметр 'query' пустой или некорректный"},
        404: {"description": "Индексная база или документ не найдены"},
        500: {"description": "Ошибка при поиске в базе"},
    },
)
async def search_chunks(request: Request, body: ChunkSearchRequest, _: str = Depends(get_current_user)):
    query = body.query.strip()
    if not query:
        await request.app.state.log.log_error("base", "Пустой параметр query при поиске чанков")
        raise HTTPException(status_code=400, detail="Параметр 'query' не может быть пустым")

    base: Base = request.app.state.base
    log = request.app.state.log

    try:
        results_raw: List[Dict[str, Any]] = await base.search_chunks(query=query, k=body.k)
        await log.log_info("base", f"Найдено {len(results_raw)} релевантных чанков для запроса")
        return {"results": results_raw}
    except FileNotFoundError as e:
        await log.log_error("base", f"Индекс или документ не найдены: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log.log_error("base", f"Ошибка при поиске чанков: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при поиске: {str(e)}")


@router.post(
    "/rebuild",
    summary="Пересоздать индекс",
    responses={
        200: {"description": "База успешно пересоздана"},
        404: {"description": "Документ для индексации не найден"},
        500: {"description": "Ошибка при пересоздании базы"},
    },
)
async def rebuild_index(request: Request, _: str = Depends(get_current_user)):
    base: Base = request.app.state.base
    log = request.app.state.log

    try:
        await base.rebuild_index()
        await log.log_info("base", "Индекс успешно пересоздан")
        return {"status": "ok", "message": "База успешно пересоздана"}
    except FileNotFoundError as e:
        await log.log_error("base", f"Документ для индексации не найден: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log.log_error("base", f"Ошибка при пересоздании базы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при пересоздании базы: {str(e)}")


@router.post(
    "/ask",
    summary="Задать вопрос базе знаний",
    responses={
        200: {"description": "Ответ успешно получен"},
        400: {"description": "Параметр 'query' пустой или некорректный"},
        404: {"description": "База знаний или документ не найдены"},
        500: {"description": "Ошибка при обращении к GPT"},
    },
)
async def ask_question(request: Request, body: ChunkSearchRequest, _: str = Depends(get_current_user)):
    query = body.query.strip()
    if not query:
        await request.app.state.log.log_error("base", "Пустой параметр query при обращении к GPT")
        raise HTTPException(status_code=400, detail="Параметр 'query' не может быть пустым")

    base: Base = request.app.state.base
    log = request.app.state.log

    system_prompt = "Ты ассистент, отвечающий на вопросы по базе знаний."

    try:
        answer = await ask(system_prompt, user_question=query, request=request, k=body.k)
        await log.log_info("base", f"GPT сгенерировал ответ на запрос: {query[:50]}...")
        return {"answer": answer}
    except FileNotFoundError as e:
        await log.log_error("base", f"Документ или база не найдены: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        await log.log_error("base", f"Ошибка при обращении к GPT: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обращении к GPT: {str(e)}")

# ==========================================================
# Работа с файлом "base/База знаний.md" через маршрут /faq
# ==========================================================

class BaseContentRequest(BaseModel):
    text: str
    
async def admin_required(user=Depends(get_current_user)):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Доступ запрещён: требуется администратор")
    return user    
@router.get(
    "/faq",
    summary="Прочитать текст из FAQ",
    responses={
        200: {"description": "Содержимое файла успешно возвращено", "content": {"application/json": {"example": {"text": "Текст базы знаний..."}}}},
        404: {"description": "Файл не найден"},
        500: {"description": "Ошибка сервера"},
    },
)
async def read_faq(request: Request, user=Depends(admin_required)):
    base: Base = request.app.state.base
    log = request.app.state.log
    try:
        text = await base.base_read()
        if not text:
            raise HTTPException(status_code=404, detail="Файл базы знаний не найден")
        await log.log_info("faq", f"Файл базы прочитан, длина текста {len(text)}")
        return {"text": text}
    except Exception as e:
        await log.log_error("faq", f"Ошибка чтения базы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка чтения базы: {str(e)}")

'''
@router.post(
    "/faq",
    summary="Записать новый текст в FAQ",
    responses={
        200: {"description": "Текст успешно сохранён", "content": {"application/json": {"example": {"status": "ok"}}}},
        400: {"description": "Некорректные данные"},
        500: {"description": "Ошибка сервера"},
    },
)
async def save_faq(request: Request, body: BaseContentRequest, user=Depends(admin_required)):
    base: Base = request.app.state.base
    log = request.app.state.log
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Параметр 'text' не может быть пустым")
    try:
        await base.base_save(body.text)
        await log.log_info("faq", f"Файл базы сохранён, длина текста {len(body.text)}")
        return {"status": "ok"}
    except Exception as e:
        await log.log_error("faq", f"Ошибка сохранения базы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка сохранения базы: {str(e)}")
'''

@router.put(
    "/faq",
    summary="Перезаписать текст в FAQ",
    responses={
        200: {"description": "Файл успешно перезаписан", "content": {"application/json": {"example": {"status": "ok"}}}},
        400: {"description": "Некорректные данные"},
        500: {"description": "Ошибка сервера"},
    },
)
async def update_faq(request: Request, body: BaseContentRequest, user=Depends(admin_required)):
    base: Base = request.app.state.base
    log = request.app.state.log
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="Параметр 'text' не может быть пустым")
    try:
        await base.base_save(body.text)
        await log.log_info("faq", f"Файл базы перезаписан, длина текста {len(body.text)}")
        return {"status": "ok"}
    except Exception as e:
        await log.log_error("faq", f"Ошибка перезаписи базы: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Ошибка перезаписи базы: {str(e)}")