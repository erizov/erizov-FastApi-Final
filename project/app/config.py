# app/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENAI_API_KEY: str
    OPENAI_MODEL: str
    AUTH_SECRET_KEY: str
    AUTH_TOKEN_EXPIRE_MINUTES: int
    AUTH_LOGIN: str
    AUTH_PASSWORD: str
    
    DATABASE_URL: str       # добавляем URL базы
    BASE_LOCAL_PATH: str    # путь к файлу базы знаний
    BASE_LOCAL_INDEX: str   # путь к базе знаний FAISS
    
    LOG_PRINT: str = "1"
    LOG_PRINT_DB: str = "0"
    LOG_PRINT_STEP: str = "0"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"   
    )

settings = Settings()