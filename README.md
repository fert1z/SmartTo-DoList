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
# .venv\Scripts\activate  # Windows
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Скопируйте пример конфигурации и задайте переменные:

```bash
cp .env.example .env
```

Отредактируйте `.env`, особенно `SECRET_KEY`. Для локальной разработки можно оставить `DATABASE_URL` без изменений.

5. Инициализируйте базу данных:

```bash
export FLASK_APP=wsgi.py
flask init-database
```

6. Запустите приложение:

**Для разработки (локально):**

```bash
export FLASK_APP=wsgi.py
flask run --debug
```

## Развертывание (Production)

### База данных

Для production-среды **настоятельно рекомендуется использовать PostgreSQL** вместо SQLite. Бесплатные PaaS-сервисы (например, Render, Heroku) имеют эфемерную файловую систему, что приведет к **потере всех данных** в SQLite при каждом перезапуске или обновлении сервера.

1.  Создайте внешнюю базу данных PostgreSQL (например, на [Render](https://render.com/docs/databases#creating-a-database) или [ElephantSQL](https://www.elephantsql.com/)).
2.  Получите URL для подключения к вашей базе данных.
3.  Установите этот URL в качестве переменной окружения `DATABASE_URL` на вашем хостинге.

Приложение автоматически определит и будет использовать `DATABASE_URL`.

### Запуск в продакшене

**С помощью Gunicorn:**

```bash
gunicorn wsgi:app
```

**С помощью скрипта `start.sh`:**

Скрипт `start.sh` запускает и веб-сервер (через Gunicorn), и Telegram-бота. Это удобный способ для простого развертывания.

```bash
chmod +x start.sh
./start.sh
```

## Telegram-бот (опционально)

Запустите Telegram-бота, если вы настроили `TELEGRAM_BOT_TOKEN` (не требуется, если вы используете скрипт `start.sh`):

```bash
python -m tg_bot.run
```

## Переменные окружения

Параметры задаются через `.env` или системные переменные.

- `SECRET_KEY` — обязательный ключ для Flask-сессий
- `FLASK_ENV` — `development`, `production`, `testing`
- `DATABASE_URL` — адрес базы данных, по умолчанию `sqlite:///instance/users.db`. **Обязательно установите для продакшена!**
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

- `./start.sh` — запуск приложения (gunicorn) и Telegram-бота
- `export FLASK_APP=wsgi.py && flask init-database` — создание базы данных
- `export FLASK_APP=wsgi.py && flask run --debug` — запустить приложение в режиме разработки
- `gunicorn wsgi:app` — запустить приложение для продакшена
- `python -m tg_bot.run` — запустить Telegram-бота
- `.venv/bin/python -m pytest -q` — запустить тесты

## Структура проекта

- `app/` — основной код Flask-приложения
- `tg_bot/` — Telegram-бот и связанные утилиты
- `app/templates/` — HTML-шаблоны
- `app/static/` — стили и скрипты
- `start.sh` — скрипт для одновременного запуска веб-сервера и бота
- `wsgi.py` — WSGI-точка входа для сервера
- `init_db.py` — утилита для создания базы данных (устарела, используйте flask init-database)
- `tests/` — тесты pytest

## Лицензия

MIT. Смотрите файл `LICENSE`.