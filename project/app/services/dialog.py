# app/services/dialog.py

import json
import re
from typing import Optional, Tuple, List, Dict
from fastapi import Request
from app.config import settings

from app.services.gpt import gpt_request
from app.services.profile import create_lead_service, read_lead_service, update_lead_service
from app.schemas.lead import LeadCreate, LeadBase

from app.services.assistant import DIALOG_SYS_PROMPT
from app.services.order import read_orders_service
from app.utils.db_service import execute_sql
from datetime import datetime
import random

class AssistantDialog:
    """
    Класс, управляющий диалогом с ассистентом для конкретного client_id.
    Основные обязанности:
      - загрузить lead и историю (один запрос),
      - добавить сообщение пользователя в локальную историю,
      - вызвать Dispatcher -> messages для формирования промпта,
      - выполнить поиск в базе (если есть) и добавить контекст (если найден),
      - отправить messages в gpt_request,
      - распарсить JSON-ответ модели (model_answer, motivation, step),
      - сохранить и lead (step/motive) и историю ОДНИМ вызовом.
    """

    def __init__(self, client_id: int, request: Request):
        self.client_id = client_id
        self.request = request
        # self.base и self.log берём из состояния приложения (middleware/инъекция)
        self.base = request.app.state.base if getattr(request.app.state, "base", None) else None
        self.log = request.app.state.log if getattr(request.app.state, "log", None) else None
        # локальная история в виде списка dict: {"role": "user"|"assistant", "content": "..."}
        self.dialog_history: List[Dict] = []

    # ------------------------------
    # Загрузка истории и lead — ОДИН вызов
    # ------------------------------
    async def load_history(self) -> Tuple[Optional[object], List[Dict]]:
        """
        Читает lead из профиля и возвращает кортеж (lead, dialog_history).
        Если записи нет или при ошибке — возвращает (None, []).
        Это предотвращает двойное чтение профиля в step().
        """
        try:
            lead = await read_lead_service(self.client_id, self.request)
            # Если у lead есть поле log — ожидаем JSON-строку
            if getattr(lead, "log", None):
                try:
                    history = json.loads(lead.log)
                    # защита: если в БД лежит не список — приводим к пустому
                    if isinstance(history, list):
                        return lead, history
                    else:
                        return lead, []
                except Exception:
                    # если парсинг сломался — возвращаем пустую историю, но сохраним lead
                    return lead, []
            else:
                return lead, []
        except Exception:
            # если чтение lead не удалось (нет записи или ошибка) — вернуть пустые значения
            return None, []

    # -------------------------
    # Сохранение истории и lead
    # -------------------------
    async def save_history(self, lead: Optional[object]):
        """
        Сохраняет в профиль (lead) одновременно:
          - лог диалога (self.dialog_history)
          - данные профиля: lead
        Логика:
          - если lead существует -> update_lead_service
          - если lead нет -> create_lead_service
        Это предотвращает двойную запись (сначала лог, потом отдельно поля lead).
        """
        # подготовка полей для создания/обновления
        payload = {"log": json.dumps(self.dialog_history, ensure_ascii=False)}

        # Создаём объекты схем только с теми полями, что нужны
        if lead:
            # Подготовим LeadBase с доступными полями (LeadBase должен поддерживать соответствующие поля)
            lead_data = LeadBase(**payload)
            await update_lead_service(self.client_id, lead_data, self.request)
        else:
            # Создаём новую запись (LeadCreate) — обязательно указываем id
            payload["id"] = self.client_id
            lead_create = LeadCreate(**payload)
            await create_lead_service(lead_create, self.request)

    # ------------------------------
    # Утилита добавления сообщения в локальную историю
    # ------------------------------
    def add_message(self, role: str, message: str):
        """
        Добавляет сообщение в локальную историю в формате:
          {"role": role, "content": message}
        """
        self.dialog_history.append({"role": role, "content": message})

    # ---------------------------------
    # Очистка диалога и профиля клиента
    # ---------------------------------     
    async def clear_dialog(self):
        """Полностью очищает профиль клиента и диалог, оставляя только id."""
        # очищаем историю в памяти
        self.dialog_history = []

        # создаём пустую заготовку профиля
        empty_lead = LeadBase(
            name=None,
            contact=None,
            log=json.dumps([], ensure_ascii=False),  
        )

        # пробуем обновить, если лид уже есть
        try:
            existing_lead = await read_lead_service(self.client_id, self.request)
        except Exception:
            existing_lead = None

        if existing_lead:
            await update_lead_service(self.client_id, empty_lead, self.request)
            if self.log:
                await self.log.log_info("dialog", "Лид очищен", {"lead_id": self.client_id})
        else:
            # если лида ещё не было — создаём пустого
            from app.schemas.lead import LeadCreate
            empty_create = LeadCreate(
                id=self.client_id,
                **empty_lead.model_dump()
            )
            await create_lead_service(empty_create, self.request)
            if self.log:
                await self.log.log_info("dialog", "Создан пустой лид", {"lead_id": self.client_id})        

    # ------------------------------
    # Основной шаг диалога
    # ------------------------------  
    async def step(self, user_input: str) -> str:
        """
        Выполняет один шаг диалога:
        - Загружает lead и историю
        - Читает FAQ и релевантные чанки из базы знаний
        - Формирует messages (system + user)
        - Отправляет запрос к GPT
        - Сохраняет lead и историю
        """
        if self.log:
            await self.log.log_info("dialog_step", "START step()", {
                "client_id": self.client_id, "user_input": user_input
            })

        # ---- 1. Загружаем lead и историю ----
        lead, history = await self.load_history()
        self.dialog_history = history or []
        self.add_message("user", user_input)
        
        # ---- 2. Загружаем список заказов ----
        orders_text = "— заказы не найдены —"
        try:
            orders = await read_orders_service(self.request, limit=50)
            formatted_orders = []
            for o in orders:
                if o.status == "отменен":
                    continue  # пропускаем отменённые
                formatted_orders.append(
                    f"#{o.id}: {o.date or '-'} | {o.customer or '-'} | {o.phone or '-'} | "
                    f"{o.products or '-'} | {o.sum or '-'} | {o.status or '-'} | "
                    f"{o.payment or '-'} | {o.delivery or '-'} | {o.track or '-'}"
                )
            if formatted_orders:
                orders_text = "\n".join(formatted_orders)
        except Exception as e:
            orders_text = f"Ошибка чтения заказов: {e}"
            if self.log:
                await self.log.log_error("dialog_step", orders_text)     

        # ---- 3. Читаем базу знаний (FAQ и FAISS чанки) ----
        faq_text = ""
        chunks_text = ""
        if self.base:
            try:
                faq_text = await self.base.base_read()
                if not faq_text.strip():
                    faq_text = "База знаний пуста."

                search_results = await self.base.search_chunks(user_input, k=5)
                if search_results:
                    chunks_text = "\n\n".join([
                        f"- (score={r['score']:.3f}) {r['content']}" for r in search_results
                    ])
                else:
                    chunks_text = "Релевантные фрагменты не найдены."
            except Exception as e:
                faq_text = f"Ошибка чтения базы знаний: {e}"
                if self.log:
                    await self.log.log_error("dialog_step", faq_text)

        # ---- 4. Собираем историю в текст ----
        dialog_text = "\n".join(
            [f"{m['role']}: {m['content']}" for m in self.dialog_history]
        ) if self.dialog_history else "— диалог отсутствует —"

        # ---- 5. Формируем messages ----
        current_date = datetime.now().strftime("%Y-%m-%d")
        track_number = random.randint(100000, 999999)
        messages = [
            {"role": "system", "content": DIALOG_SYS_PROMPT.strip()},
            {"role": "system", "content": f"Текущая дата: {current_date}"},
            {"role": "system", "content": f"Трек-номер для нового заказа: {track_number}"},            
            {"role": "system", "content": f"Текущие заказы (таблица order):\n\n{orders_text}"},
            {"role": "system", "content": f"FAQ:\n\n{faq_text[:4000]}"},
            {"role": "system", "content": f"Релевантные фрагменты базы знаний:\n\n{chunks_text[:4000]}"},
            {"role": "system", "content": f"История диалога:\n\n{dialog_text[:2000]}"},
        ]
        
        # Если имя и контакт лида неизвестны — добавить системное представление
        if not lead.name and not lead.contact:
            messages.insert(
                len(messages),  # вставляем перед user
                {
                    "role": "system",
                    "content": (
                        "Если клиент ещё не представился, начни диалог с приветствия и представления от имени ассистента. "
                        "Пример: 'Здравствуйте! Меня зовут Астра, я консультант магазина товаров для животных. "
                        "Как могу к вам обращаться?'"
                    ),
                }
            )    

        # Вставляем данные клиента, если они уже известны
        if lead and (lead.name or lead.contact):
            known_info = f"Известные данные клиента:\nИмя: {lead.name or 'не указано'}\nКонтакт: {lead.contact or 'не указан'}"
            messages.append({"role": "system", "content": known_info})

        # Теперь добавляем само сообщение пользователя
        messages.append({
            "role": "user",
            "content": f"Ответ строго в формате JSON!\n\nВопрос пользователя:\n\n{user_input}"
        })

        # ---- 6. Запрос к GPT ----
        raw_response = await gpt_request(messages)
        await self.log.log_info("dialog_step", "Model raw response", raw_response)

        # ---- 7. Обрабатываем ответ ----
        try:
            # очищаем управляющие символы, которые ломают JSON
            clean_response = re.sub(r'[\x00-\x1f]+', '', raw_response)
            response_data = json.loads(clean_response)

            model_answer = response_data.get("model_answer", "")
            report = response_data.get("report", "")
            sql_command = response_data.get("sql")
            await self.log.log_info("dialog_step", "report", report)

        except Exception as e:
            # на случай ошибки разбора JSON
            response_data = {}  # всегда существует
            model_answer = f"Ошибка разбора ответа модели: {e}"
            sql_command = None
            await self.log.log_error("dialog_step", model_answer)

        await self.log.log_info("dialog_step", "sql_command", sql_command)          

        # ---- 8. Выполняем SQL ----
        if sql_command and isinstance(sql_command, str):
            success = await execute_sql(sql_command)
            if success:
                await self.log.log_info("dialog_step", "SQL выполнен успешно", {"sql": sql_command})
            else:
                await self.log.log_error("dialog_step", "Ошибка выполнения SQL", {"sql": sql_command})

        # ---- 9. Обновляем lead ----
        if lead:
            lead.name = response_data.get("user_name", lead.name)
            lead.contact = response_data.get("user_contact", lead.contact)
            await self.log.log_info("dialog_step", "Lead updated", {
                "lead.name": lead.name, "lead.contact": lead.contact
            })

        # ---- 10. Сохраняем историю ----
        self.add_message("assistant", model_answer)
        await self.save_history(lead=lead)

        await self.log.log_info("dialog_step", "END step()", {"model_answer": model_answer})
        return model_answer

