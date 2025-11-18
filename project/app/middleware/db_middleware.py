# app/middleware/db_middleware.py

from types import SimpleNamespace
from starlette.types import ASGIApp, Receive, Scope, Send
from app.utils.database import AsyncSessionLocal

class DBSessionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # убедимся, что state есть
        state = scope.setdefault("state", {})
        # просто кладём сессию в словарь
        state["db"] = AsyncSessionLocal()
        try:
            await self.app(scope, receive, send)
        finally:
            # закрываем сессию только после завершения запроса
            await state["db"].close()
