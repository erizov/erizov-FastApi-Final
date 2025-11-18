# app/services/db_service.py

from app.utils.database import AsyncSessionLocal
from sqlalchemy import text

async def execute_sql(sql: str) -> bool:
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text(sql))
            await session.commit()
            return True
        except Exception as e:
            import logging
            logging.error(f"SQL Error: {e} | SQL: {sql}")
            return False