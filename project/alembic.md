# Справочник команд Alembic

Alembic — это инструмент для управления миграциями базы данных SQLAlchemy. Ниже приведён полный справочник основных команд.

---

## 1. Инициализация Alembic

```bash
alembic init <директория>
```

* Создаёт структуру Alembic: `alembic.ini`, папку `versions`, `env.py`.
* Пример:

```bash
alembic init alembic
```

---

## 2. Создание ревизий

### 2.1 Автогенерация

```bash
alembic revision --autogenerate -m "описание"
```

* Создаёт файл миграции с SQL-командами, основанными на разнице между моделями и базой.
* Пример:

```bash
alembic revision --autogenerate -m "add model_answer to leads"
```

### 2.2 Пустая ревизия

```bash
alembic revision -m "описание"
```

* Создаёт пустой файл миграции с `upgrade()` и `downgrade()`.

---

## 3. Применение миграций

### 3.1 Применить все миграции до последней

```bash
alembic upgrade head
```

### 3.2 Применить до конкретной ревизии

```bash
alembic upgrade <revision_id>
```

* Пример:

```bash
alembic upgrade 20250930_add_model_answer_to_leads
```

### 3.3 Откат до предыдущей ревизии

```bash
alembic downgrade -1
```

### 3.4 Откат до конкретной ревизии

```bash
alembic downgrade <revision_id>
```

---

## 4. Метки версии

### 4.1 Присвоить текущую версию без применения миграций

```bash
alembic stamp head
```

* Говорит Alembic, что база синхронизирована с последней ревизией.

### 4.2 Присвоить конкретную ревизию

```bash
alembic stamp <revision_id>
```

---

## 5. Просмотр состояния

```bash
alembic current
```

* Показывает текущую версию базы.

```bash
alembic history
```

* Выводит историю всех ревизий.

```bash
alembic heads
```

* Показывает последние ревизии (head) в ветке.

```bash
alembic branches
```

* Показывает ветки миграций, если их несколько.

---

## 6. Управление миграциями

### 6.1 Объединение веток (merge)

```bash
alembic merge -m "merge message" <rev1> <rev2>
```

* Объединяет несколько ревизий в одну.

### 6.2 Просмотр SQL без выполнения

```bash
alembic upgrade head --sql
alembic downgrade -1 --sql
```

* Генерирует SQL, который Alembic выполнит, но не применяет его.

---

## 7. Полезные параметры

* `--autogenerate` — автогенерация SQL по метаданным моделей.
* `-m "message"` — сообщение для ревизии.
* `--sql` — вывести SQL вместо применения.
* `--rev-id <id>` — задать собственный идентификатор ревизии.

---

## 8. Примеры

1. Создать миграцию для новой колонки:

```bash
alembic revision --autogenerate -m "add model_answer to leads"
alembic upgrade head
```

2. Откатить последнюю миграцию:

```bash
alembic downgrade -1
```

3. Присвоить текущую базу последней версии:

```bash
alembic stamp head
```
