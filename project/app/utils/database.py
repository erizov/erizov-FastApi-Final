# app/utils/database.py

# app/utils/database.py

import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession  
from sqlalchemy.orm import sessionmaker, declarative_base  
from sqlalchemy.future import select  
from sqlalchemy import text
from app.config import settings
from app.utils.security import hash_password  

# ────────────── Base для моделей ──────────────
Base = declarative_base()  # базовый класс для всех моделей SQLAlchemy

# ────────────── URL базы данных ──────────────
SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

# ────────────── Асинхронный движок ──────────────
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False  # True можно включить для отладки SQL
)

# ────────────── Асинхронная сессия ──────────────
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=bool(settings.LOG_PRINT_DB)  # флаг автоматического "expire" после коммита
)

# ────────────── Инициализация базы данных ──────────────
async def init_db():
    """
    Создаёт все таблицы в базе данных (если ещё не созданы)
    Проверяет наличие хотя бы одного администратора
        - Если админ отсутствует:
            • Удаляет все существующие записи
            • Создаёт первого администратора с логином "admin" и паролем "admin"
            • Пароль хранится в виде хэша
    """
    # Создаём таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Проверяем наличие админа
    from app.models.lead import Lead
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lead))
        users = result.scalars().all()

        if not any(u.is_admin for u in users):
            for u in users:
                await session.delete(u)
            await session.commit()

            admin_user = Lead(
                name="Administrator",
                login="admin",
                password=hash_password("admin"),
                is_admin=True
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)
            print("Создан первый админ admin/admin после очистки таблицы")

