#!/bin/bash

echo "🚀 Запуск SmartTo-DoList..."

# Активация виртуального окружения, если мы не в Docker/PaaS
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Запуск Flask-приложения в фоне (Production)
echo "🌐 Запуск веб-сервера (Gunicorn)..."
# В облачных средах (Render, Railway) .venv может не быть, gunicorn должен быть в PATH
GUNICORN_PATH="gunicorn"
if [ -f ".venv/bin/gunicorn" ]; then
    GUNICORN_PATH=".venv/bin/gunicorn"
fi
$GUNICORN_PATH wsgi:app --bind 0.0.0.0:${PORT:-10000} &
APP_PID=$!

# Запуск Telegram-бота в фоне (если настроен токен)
# Проверяем переменную окружения, а не файл .env
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "🤖 Запуск Telegram-бота..."
    python -m tg_bot.run &
    BOT_PID=$!
else
    echo "⚠️ TELEGRAM_BOT_TOKEN не настроен, бот не запущен."
    BOT_PID=""
fi

# Корректное завершение всех процессов по Ctrl+C и SIGTERM
trap "echo 'Gracefully stopping...'; kill $APP_PID ${BOT_PID:-}; exit" INT TERM

# Ожидаем завершения любого из фоновых процессов
wait -n $APP_PID ${BOT_PID:-}