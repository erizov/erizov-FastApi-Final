# app/routes/auth.py

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.exc import IntegrityError
from app.utils.security import hash_password, verify_password
from app.config import settings
from app.schemas.user import UserCreate, UserUpdate, UserResponse
from app.services.profile import (
    create_lead_service,
    read_leads_service,
    read_lead_service,
    update_lead_service,
    delete_lead_service
)

router = APIRouter()

# ────────────── JWT и пароли ──────────────
SECRET_KEY = settings.AUTH_SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = settings.AUTH_TOKEN_EXPIRE_MINUTES
ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Создаёт JWT токен на основе данных пользователя и времени жизни токена.
    Вход: dict (например {"sub": "username"})
    Выход: JWT строка
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme), request: Request = None):
    """
    Проверяет JWT токен и возвращает пользователя (username, is_admin).

    **Статусы:**
    - 200 OK – токен действителен
    - 401 Unauthorized – токен истёк, неверный или отсутствует username
    - 500 Internal Server Error – внутренняя ошибка

    Возвращает: объект пользователя с полями login и is_admin
    """
    try:
        payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        login: str = payload.get("sub")
        if login is None:
            if request and hasattr(request.app.state, "log"):
                await request.app.state.log.log_error("auth", "Токен не содержит username")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except ExpiredSignatureError:
        if request and hasattr(request.app.state, "log"):
            await request.app.state.log.log_warning("auth", "Токен истёк")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except InvalidTokenError:
        if request and hasattr(request.app.state, "log"):
            await request.app.state.log.log_warning("auth", "Неверный токен")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalid")

    users = await read_leads_service(request)
    user = next((u for u in users if u.login == login), None)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if request and hasattr(request.app.state, "log"):
        await request.app.state.log.log_info("auth", f"Токен проверен: {login}")

    return user


# ────────────── TOKEN ──────────────
@router.post(
    "/token",
    summary="Получение JWT токена (авторизация пользователя)",
    responses={
        200: {
            "description": "✅ Токен успешно получен. Возвращает access_token, token_type и данные пользователя.",
            "content": {
                "application/json": {
                    "example": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                        "token_type": "bearer",
                        "user": {
                            "id": 1,
                            "name": "Administrator",
                            "login": "admin",
                            "is_admin": True
                        }
                    }
                }
            }
        },
        401: {"description": "❌ Неверный логин или пароль"},
        422: {"description": "⚠️ Ошибка валидации входных данных (например, пустой username или password)"},
        500: {"description": "💥 Внутренняя ошибка сервера"}
    }
)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    """
    Авторизация пользователя и получение JWT токена.

    **Описание:**  
    Проверяет логин и пароль пользователя.  
    Если данные корректны — возвращает JWT токен, тип токена и базовую информацию о пользователе.

    **Входные данные (form-data):**  
    - `username`: str — логин пользователя  
    - `password`: str — пароль пользователя  

    **Выходные данные (JSON):**  
    - `access_token`: str — JWT токен для авторизации  
    - `token_type`: str — всегда `"bearer"`  
    - `user`: object  
        - `id`: int — уникальный идентификатор пользователя  
        - `name`: str — имя пользователя  
        - `login`: str — логин  
        - `is_admin`: bool — признак администратора  

    **Коды ответа:**  
    - `200`: токен успешно выдан  
    - `401`: неверный логин или пароль  
    - `422`: ошибка валидации запроса  
    - `500`: внутренняя ошибка сервера
    """
    log = getattr(request.app.state, "log", None)
    try:
        # Получаем всех пользователей
        users = await read_leads_service(request)
        user = next((u for u in users if u.login == form_data.username), None)

        # Проверка логина и пароля
        if not user or not verify_password(form_data.password, getattr(user, "password", "")):
            if log:
                await log.log_warning("auth", "Неудачная попытка входа", {"username": form_data.username})
            raise HTTPException(
                status_code=401,
                detail="Неверный логин или пароль",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # Создание токена с истечением срока действия
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.login},
            expires_delta=access_token_expires
        )

        if log:
            await log.log_info("auth", "Пользователь успешно авторизован", {"user": user})

        # Возвращаем токен и информацию о пользователе
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "name": user.name,
                "login": user.login,
                "is_admin": user.is_admin
            }
        }

    except Exception as e:
        if log:
            await log.log_error("auth", f"Ошибка при получении токена: {e}", {"username": form_data.username})
        raise HTTPException(
            status_code=500,
            detail="Внутренняя ошибка сервера"
        )
    
# ────────────── Регистрация обычного пользователя ──────────────
@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Регистрация нового пользователя",
    responses={
        201: {"description": "Пользователь успешно зарегистрирован"},
        400: {"description": "Логин уже занят или неверные данные"},
        422: {"description": "Ошибка валидации"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def register_user(user: UserCreate, request: Request = None):
    """
    Регистрация нового пользователя.

    - Все новые пользователи **по умолчанию обычные** (`is_admin=False`).
    - Пароль хэшируется перед сохранением.
    """
    user.is_admin = False
    if user.password:
        user.password = hash_password(user.password)

    try:
        created_user = await create_lead_service(user, request)
        return created_user
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Пользователь с логином '{user.login}' уже существует"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сервера: {e}"
        )    

# ────────────── CRUD USERS ──────────────

# ────────────── Создание пользователя (только для админа) ──────────────
@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="Создание пользователя (только администратор)",
    responses={
        201: {"description": "Пользователь успешно создан"},
        400: {"description": "Некорректные данные при создании"},
        401: {"description": "Отсутствует или неверный токен авторизации"},
        403: {"description": "Обычный пользователь не может создавать администраторов"},
        409: {"description": "Пользователь с таким логином уже существует"},
        422: {"description": "Ошибка валидации данных"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def create_user(
    user: UserCreate,
    current_user=Depends(get_current_user),
    request: Request = None
):
    """
    ## Создание нового пользователя

    - Только **администратор** может создавать других пользователей.
    - Если **обычный пользователь** пытается создать **администратора**, возвращается `403`.
    - Если логин уже существует, возвращается `409 Conflict`.
    - Пароль всегда хэшируется перед сохранением.
    """

    # Проверка прав
    if not current_user.is_admin:
        # обычный пользователь не может создавать администраторов
        if user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Обычный пользователь не может создавать администраторов"
            )
        # принудительно делаем обычным
        user.is_admin = False

    # Хэширование пароля
    if user.password:
        user.password = hash_password(user.password)

    # Попытка сохранить пользователя
    try:
        created_user = await create_lead_service(user, request)
        return created_user

    # Ошибка уникальности логина
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь с логином '{user.login}' уже существует"
        )

    # Прочие ошибки
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сервера: {e}"
        )


# GET USERS
@router.get(
    "/users",
    response_model=List[UserResponse],
    status_code=200,
    summary="Список всех пользователей (только админ)",
    responses={
        200: {"description": "Список пользователей"},
        401: {"description": "Токен невалиден"},
        403: {"description": "Доступ запрещён для обычного пользователя"},
        500: {"description": "Внутренняя ошибка сервера"}
    }
)
async def get_users(current_user=Depends(get_current_user), request: Request = None):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return await read_leads_service(request)


# GET SINGLE USER
@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    status_code=200,
    summary="Получение пользователя по ID",
    responses={
        200: {"description": "Пользователь найден"},
        401: {"description": "Токен невалиден"},
        403: {"description": "Обычный пользователь не может получить чужого"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Ошибка сервера"}
    }
)
async def get_user(user_id: int, current_user=Depends(get_current_user), request: Request = None):
    user = await read_lead_service(user_id, request)
    if not current_user.is_admin and user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return user


# UPDATE USER
@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    status_code=200,
    summary="Обновление пользователя",
    responses={
        200: {"description": "Пользователь успешно обновлён"},
        400: {"description": "Некорректные данные при обновлении"},
        401: {"description": "Отсутствует или неверный токен авторизации"},
        403: {"description": "Обычный пользователь не может редактировать чужого или менять is_admin"},
        404: {"description": "Пользователь не найден"},
        409: {"description": "Пользователь с таким логином уже существует"},
        422: {"description": "Ошибка валидации данных"},
        500: {"description": "Внутренняя ошибка сервера"},
    }
)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user=Depends(get_current_user),
    request: Request = None
):
    """
    ## Обновление пользователя

    - Администратор может редактировать любого пользователя, включая флаг `is_admin`.
    - Обычный пользователь может редактировать только себя, флаг `is_admin` нельзя менять.
    - Проверка уникальности логина: если логин уже занят, возвращается `409 Conflict`.
    - Пароль всегда хэшируется перед сохранением.
    """
    # Проверка прав обычного пользователя
    if not current_user.is_admin:
        if user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Обычный пользователь не может редактировать чужого")
        if user_update.is_admin:
            raise HTTPException(status_code=403, detail="Обычный пользователь не может менять is_admin")

    # Хэширование пароля
    if user_update.password:
        user_update.password = hash_password(user_update.password)

    try:
        # Получаем текущего пользователя через сервис
        db_user = await read_lead_service(user_id, request)
        if db_user is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")

        # Применяем обновления
        for key, value in user_update.dict(exclude_unset=True).items():
            setattr(db_user, key, value)

        # Сохраняем изменения
        request.state.db.add(db_user)
        await request.state.db.commit()
        await request.state.db.refresh(db_user)

        # Возвращаем через Pydantic-схему
        return UserResponse.model_validate(db_user)  # Pydantic v2

    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь с логином '{user_update.login}' уже существует"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка сервера: {e}"
        )

# DELETE USER
@router.delete(
    "/users/{user_id}",
    status_code=200,
    summary="Удаление пользователя",
    responses={
        200: {"description": "Пользователь удалён"},
        401: {"description": "Токен невалиден"},
        403: {"description": "Доступ запрещён"},
        404: {"description": "Пользователь не найден"},
        500: {"description": "Ошибка сервера"}
    }
)
async def delete_user(user_id: int, current_user=Depends(get_current_user), request: Request = None):
    """
    Удаление пользователя.
    - Админ может удалить любого
    - Обычный пользователь может удалить только себя
    """
    if not current_user.is_admin and user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    await delete_lead_service(user_id, request)
    return {"detail": "User deleted"}
