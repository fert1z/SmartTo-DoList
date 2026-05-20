# SmartTo-DoList

Приложение для управления задачами и напоминаниями с опциональной поддержкой Telegram-уведомлений.

Коротко: лёгкое Flask-приложение с регистрацией/логином, CRUD для задач и веб-привязкой Telegram аккаунта.

## Что я добавил/проверил

- Обновил инструкцию по установке и запуску
- Добавил `LICENSE` (MIT)
- Указал команды для инициализации БД и запуска бота

## Требования

- Python 3.8+ (рекомендовано 3.11+)
- SQLite (по умолчанию) или любая СУБД, поддерживаемая SQLAlchemy
- Рекомендуется виртуальное окружение (`venv`/`.venv`)

## Быстрый старт (локально)

1) Клонируйте репозиторий:

```bash
git clone https://github.com/fert1z/SmartTo-DoList.git
cd SmartTo-DoList
```

2) Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\\Scripts\\activate   # Windows
```

3) Установите зависимости:

```bash
pip install -r requirements.txt
```

4) Создайте файл окружения `.env` на основе `.env.example` и отредактируйте значения:

```bash
cp .env.example .env
# Редактируйте .env — укажите SECRET_KEY и при необходимости TELEGRAM_BOT_TOKEN
```

5) Инициализируйте базу данных:

```bash
# Вариант 1 — через helper-скрипт
python init_db.py

# Вариант 2 — через CLI Flask (если хотите использовать Flask CLI)
export FLASK_APP=wsgi.py
flask init-database
```

6) Запустите приложение (разработка):

```bash
python wsgi.py
```

Или с Flask CLI:

```bash
export FLASK_APP=wsgi.py
flask run --host=0.0.0.0 --port=5000
```

Для продакшена используйте Gunicorn:

```bash
gunicorn wsgi:app
```

7) Запуск Telegram-бота (опционально):

```bash
python -m tg_bot.run
```

## Тесты

Запуск тестов:

```bash
.venv/bin/python -m pytest -q
```

В проекте есть набор pytest-тестов — убедитесь, что `FLASK_ENV=testing` если потребуется отдельная конфигурация.

## Переменные окружения (основные)

- `SECRET_KEY` — обязательна для сессий
- `FLASK_ENV` — `development`/`production`/`testing`
- `DATABASE_URL` — URL БД (по умолчанию использует SQLite `instance/users.db`)
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота (если используете бота)

Файл `.env.example` содержит пример всех переменных, которые использует проект.

## Полезные команды

- Инициализация БД вручную: `python init_db.py`
- Запуск тестов: `.venv/bin/python -m pytest -q`
- Локальный запуск: `python wsgi.py` или `flask run`
- Запуск бота: `python -m tg_bot.run`

## Структура (коротко)

Основные папки/файлы:

- `app/` — Flask-приложение и маршруты
- `tg_bot/` — код Telegram-бота
- `templates/`, `static/` — фронтенд
- `wsgi.py` — точка входа
- `init_db.py` — быстрый скрипт для создания БД
- `tests/` — pytest

## Вклад

1. Fork репозитория
2. Создайте ветку (`feature/...`)
3. Commit и push
4. Откройте Pull Request

## Лицензия

Проект лицензируется под MIT — см. файл `LICENSE`.

## Поддержка

Откройте issue: https://github.com/fert1z/SmartTo-DoList/issues
