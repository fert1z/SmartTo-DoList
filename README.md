# SmartTo-DoList

Приложение для управления задачами и напоминаниями с поддержкой Telegram-уведомлений (привязка через одноразовый код).

## 🌟 Что умеет приложение (по текущей реализации)

- ✅ **Аутентификация**: регистрация, логин, logout
- ✅ **Задачи**: создание, получение списка, получение/обновление/удаление, отметка выполнения
- ✅ **Панель пользователя**: профиль и настройки
- ✅ **Telegram интеграция** (в части веб-привязки):
  - генерация одноразового кода привязки
  - отвязка Telegram
- 🔐 **Безопасная аутентификация**: пароли хранятся как hash (werkzeug)

> Примечание: в текущем репозитории **нет** реализации для:
> - распознавания речи
> - AI/«умных напоминаний»
> - отправки писем (mail)
> - отдельного API под `/api/tasks` в стиле REST (вместо этого используются `/tasks/*`)

## 📋 Требования

- Python **3.8+**
- Flask **3.x**
- Flask-SQLAlchemy **3.x**
- SQLite (или PostgreSQL при наличии `DATABASE_URL`)

## 🚀 Установка и запуск

### 1) Клонирование репозитория
```bash
git clone https://github.com/fert1z/SmartTo-DoList.git
cd SmartTo-DoList
```

### 2) Виртуальное окружение
```bash
python -m venv venv
# macOS/Linux
source venv/bin/activate
# Windows
# venv\Scripts\activate
```

### 3) Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4) Переменные окружения

Создайте `.env` в корне проекта (пример — `.env.example`):

```env
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-change-this

DATABASE_URL=sqlite:///instance/users.db

TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_API_URL=https://api.telegram.org

PORT=5000
HOST=0.0.0.0

# Mail-параметры в README ранее упоминались — в текущей реализации отправка писем не интегрирована.
```

### 5) Инициализация базы данных

База поднимается автоматически внутри `create_app()` (в `app/__init__.py`), включая схему/миграции.

Для ручной инициализации можно:
```bash
flask --app wsgi.py init-database
```

### 6) Запуск приложения

Для разработки:
```bash
python wsgi.py
```

Для продакшена (Gunicorn):
```bash
gunicorn wsgi:app
```

Приложение доступно по адресу:
- **http://localhost:5000** (по умолчанию)

## 📁 Структура проекта

```
SmartTo-DoList/
├── app/                        # Flask приложение (factory + blueprints)
│   ├── __init__.py             # create_app(), db init, обработчики ошибок
│   ├── models.py               # User, Task, TelegramLinkCode
│   ├── db_schema.py           # легкие миграции (ALTER TABLE без Alembic)
│   ├── utils.py                # validate_* и require_login
│   ├── logging_config.py      # логирование
│   └── routes/
│       ├── main.py            # /, /about, /dashboard, /addtask
│       ├── auth.py            # /auth/login, /auth/register, /auth/logout, /auth/forgot-password
│       ├── account.py         # /account/profile, /account/settings и Telegram привязка
│       └── tasks.py           # /tasks/* (CRUD задач)
├── instance/                  # SQLite файлы БД
├── tg_bot/                     # Telegram бот
├── templates/                 # HTML шаблоны
├── wsgi.py                     # WSGI entrypoint
├── requirements.txt
├── .env.example
├── README.md
└── tests/                     # pytest-тесты (используются pytest)
```

## 🔐 Переменные окружения (минимум)

- `SECRET_KEY` — обязательна для Flask-сессий
- `FLASK_ENV` — `development`/`production`/`testing`
- `DATABASE_URL` — для БД (по умолчанию используется SQLite в `instance/users.db`)
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `TELEGRAM_API_URL` — URL API Telegram

## 💻 Разработка

### Тесты
```bash
pytest -q
```

### Линтинг/форматирование (если настроено в окружении)
```bash
flake8 app/
pylint app/
black app/
```

## 📊 Роуты и эндпоинты (по текущей реализации)

### Страницы
- `GET /` — главная
- `GET /about` — информация о проекте
- `GET /dashboard` — панель пользователя (требует login)
- `GET /addtask` — страница создания задачи (требует login)

### Аутентификация
- `GET /auth/login`
- `POST /auth/login`
- `GET /auth/register`
- `POST /auth/register`
- `GET /auth/logout`
- `GET/POST /auth/forgot-password`

### Задачи (JSON)
- `GET/POST /tasks/new`
  - `POST` создаёт задачу (form-data поля из HTML)
- `GET /tasks/list` — список задач текущего пользователя
- `GET /tasks/<int:task_id>` — получить задачу
- `PUT /tasks/<int:task_id>` — обновить задачу
- `DELETE /tasks/<int:task_id>` — удалить задачу
- `POST /tasks/<int:task_id>/complete` — отметить выполненной

### Профиль/настройки
- `GET /account/profile`
- `GET /account/settings`

### Telegram (веб-привязка)
- `POST /account/telegram/generate-link` — получить одноразовый код и TTL
- `POST /account/telegram/unlink` — отвязать Telegram

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте ветку (`feature/...`)
3. Commit изменения
4. Push на ветку
5. Откройте Pull Request

## 📝 Лицензия

MIT.
> В репозитории в данный момент нет файла `LICENSE`, поэтому здесь убрано упоминание о нем.

## ❓ Поддержка

- Issue: https://github.com/fert1z/SmartTo-DoList/issues
