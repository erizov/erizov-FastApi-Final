# app/services/gpt.py

from openai import AsyncOpenAI
from app.config import settings
from fastapi import Request

# Инициализация клиента OpenAI
client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def gpt_request(messages: list[dict], model: str = settings.OPENAI_MODEL) -> str:
    """
    Асинхронный запрос к OpenAI ChatCompletion API.
    """
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
    )
    return response.choices[0].message.content


async def ask(system_prompt: str, user_question: str, request: Request = None, k: int = 5) -> str:
    """
    Выполняет поиск по базе знаний и спрашивает GPT.

    Args:
        system_prompt (str): system-инструкция
        user_question (str): вопрос пользователя
        request (Request, optional): FastAPI request для доступа к app.state.base и log
        k (int): количество релевантных чанков

    Returns:
        str: ответ модели
    """
    # Получаем глобальный объект base
    base = getattr(request.app.state, "base", None) if request else None
    if base is None:
        raise RuntimeError("Knowledge base не инициализирована")

    # Поиск по векторной базе
    chunks = await base.search_chunks(user_question, k=k)
    if base.log:
        await base.log.log_info("gpt_ask", "Релевантные чанки найдены",
                                {"query": user_question, "chunks_count": len(chunks)})

    # Формируем контекст
    context = "\n\n".join([c["content"] for c in chunks])
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Вопрос: {user_question}\n\nКонтекст:\n{context}"},
    ]

    # Запрос к модели
    response_text = await gpt_request(messages)
    if base.log:
        await base.log.log_info("gpt_ask", "Ответ GPT получен", {"response": response_text})

    return response_text
