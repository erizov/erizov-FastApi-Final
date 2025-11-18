# app/schemas/base.py

from pydantic import BaseModel, Field

class ChunkSearchRequest(BaseModel):
    query: str = Field(..., description="Поисковый запрос")
    k: int = Field(5, ge=1, le=50, description="Количество возвращаемых чанков (по умолчанию 5)")
