# app/utils/security.py

"""
Модуль для работы с хэшированием паролей и проверкой паролей.
Используется passlib с sha256_crypt, чтобы избежать проблем с bcrypt на Windows.
"""

from passlib.context import CryptContext

# Создаём контекст для хэширования паролей
# schemes=["sha256_crypt"] - используем SHA-256 с солью
# deprecated="auto" - автоматически помечает устаревшие схемы
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хэширует пароль.

    :param password: строка пароля пользователя
    :return: хэшированный пароль в виде строки
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет совпадение пароля с его хэшем.

    :param plain_password: строка пароля пользователя
    :param hashed_password: хэшированный пароль из базы
    :return: True если пароль совпадает с хэшем, иначе False
    """
    return pwd_context.verify(plain_password, hashed_password)
