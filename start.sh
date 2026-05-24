#!/bin/bash

echo "🚀 Запуск SmartTo-DoList..."

# Активация виртуального окружения
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "❌ Виртуальное окружение .venv не найдено. Запустите setup сначала."
    exit 1
fi

# Запуск Flask-приложения в фоне (Production)
echo "🌐 Запуск веб-сервера (Gunicorn)..."
.venv/bin/gunicorn wsgi:app --bind 0.0.0.0:${PORT:-5001} &
APP_PID=$!

# Запуск Telegram-бота в фоне (если настроен токен)
if grep -q "TELEGRAM_BOT_TOKEN=.\+" .env 2>/dev/null; then
    echo "🤖 Запуск Telegram-бота..."
    python -m tg_bot.run &
    BOT_PID=$!
else
    echo "⚠️ TELEGRAM_BOT_TOKEN не настроен, бот не запущен."
    BOT_PID=""
fi

# Корректное завершение всех процессов по Ctrl+C
trap "echo 'Stopping...'; kill $APP_PID ${BOT_PID:-}; exit" INT

wait