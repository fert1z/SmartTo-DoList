# SmartTo-DoList

Flask-приложение для управления задачами, напоминаниями и уведомлениями через Telegram.

## Что делает проект

- регистрация и аутентификация пользователей
- создание, редактирование, удаление задач
- управление статусом и сроками задач
- поддержка email-уведомлений через SMTP
- интеграция с Telegram-ботом для напоминаний
- простая локальная конфигурация через `.env`

## Быстрый старт

1. Клонируйте репозиторий:

```bash
git clone https://github.com/fert1z/SmartTo-DoList.git
cd SmartTo-DoList
```

2. Создайте и включите виртуальное окружение:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
# .venv\\Scripts\\activate  # Windows
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Скопируйте пример конфигурации и задайте переменные:

```bash
cp .env.example .env
```

Отредактируйте `.env`, особенно `SECRET_KEY` и `DATABASE_URL`. Если используется Telegram-бот, задайте `TELEGRAM_BOT_TOKEN`.

5. Инициализируйте базу данных:

```bash
python init_db.py
```

Или через Flask CLI:

```bash
export FLASK_APP=wsgi.py
flask init-database
```

6. Запустите приложение:

```bash
python wsgi.py
```

Или для разработки:

```bash
python app.py
```

Для продакшен-окружения:

```bash
gunicorn wsgi:app
```

## Telegram-бот (опционально)

Запустите Telegram-бота, если вы настроили `TELEGRAM_BOT_TOKEN`:

```bash
python -m tg_bot.run
```

## Переменные окружения

Параметры задаются через `.env` или системные переменные.

- `SECRET_KEY` — обязательный ключ для Flask-сессий
- `FLASK_ENV` — `development`, `production`, `testing`
- `DATABASE_URL` — адрес базы данных, по умолчанию `sqlite:///instance/users.db`
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота
- `TELEGRAM_API_URL` — URL API Telegram (`https://api.telegram.org`)
- `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` — SMTP-параметры для отправки почты
- `PORT` — порт, на котором запускается приложение (по умолчанию `5000`)
- `HOST` — хост для запуска (по умолчанию `0.0.0.0`)

> Старые переменные `SMTP_*` также поддерживаются для совместимости.

## Тестирование

Запустите тесты через pytest:

```bash
.venv/bin/python -m pytest -q
```

Для проверки зависимостей установите `requirements-dev.txt` и выполните `pip-audit`.

## Полезные команды

- `python init_db.py` — создать базу данных
- `python wsgi.py` — запустить приложение
- `python app.py` — запустить приложение в режиме разработки
- `export FLASK_APP=wsgi.py && flask init-database` — инициализация БД через Flask CLI
- `python -m tg_bot.run` — запустить Telegram-бота
- `.venv/bin/python -m pytest -q` — запустить тесты

## Структура проекта

- `app/` — основной код Flask-приложения
- `tg_bot/` — Telegram-бот и связанные утилиты
- `templates/`, `app/templates/` — HTML-шаблоны
- `static/`, `app/static/` — стили и скрипты
- `wsgi.py` — WSGI-точка входа для сервера
- `app.py` — упрощённый запуск для разработки
- `init_db.py` — создание и инициализация базы данных
- `tests/` — тесты pytest

## Вклад

1. Форкните репозиторий
2. Создайте ветку `feature/...`
3. Сделайте коммит и отправьте изменения
4. Откройте Pull Request

## Лицензия

MIT. Смотрите файл `LICENSE`.
