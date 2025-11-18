# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from app.utils.log import Log
from app.utils.database import init_db
from app.services.base import Base
from app.middleware.db_middleware import DBSessionMiddleware

import os
import multiprocessing

# --- загрузка переменных окружения ---
load_dotenv()

# --- sync логгер для раннего старта ---
boot_log = Log()
if os.environ.get("RUN_MAIN") == "true" or multiprocessing.current_process().name == "MainProcess":
    boot_log.log_info_sync(target="startup", message="Импорты main.py выполнены")

# ────────────── Lifespan ──────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    boot_log.log_info_sync(target="startup", message="lifespan: startup начат")

    # Инициализация БД
    await init_db()
    boot_log.log_info_sync(target="startup", message="База инициализирована")

    # Инициализация Log в state
    app.state.base = Base()
    boot_log.log_info_sync(target="startup", message="Base добавлен в app.state")

    app.state.log = Log()
    await app.state.log.log_info(target="startup", message="Async Log инициализирован")

    yield

    # shutdown
    await app.state.log.log_info(target="shutdown", message="Остановка приложения")
    await app.state.log.shutdown()
    boot_log.log_info_sync(target="shutdown", message="Log корректно завершён")

# ────────────── Создаём FastAPI приложение ──────────────
app = FastAPI(title="Lead & Assistant API", lifespan=lifespan, debug=True)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB middleware для request.state.db
app.add_middleware(DBSessionMiddleware)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

# ────────────── Подключение роутов ──────────────
from app.routes import auth, base, lead, dialog, order

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(base.router, prefix="/base", tags=["base"])
app.include_router(lead.router, prefix="/lead", tags=["lead"])
app.include_router(dialog.router, prefix="/dialog", tags=["dialog"])
app.include_router(order.router, prefix="/order", tags=["order"])

# ────────────── Запуск uvicorn ──────────────
if __name__ == "__main__":
    boot_log.log_info_sync(target="startup", message="Запуск uvicorn.run")
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        log_level="info",
        reload=True
    )
