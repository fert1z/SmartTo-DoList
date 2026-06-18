#!/bin/bash

echo "🚀 Starting SmartTo-DoList..."

# Activate virtual environment if not in Docker/PaaS
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Run Flask application (Production)
echo "🌐 Starting web server (Gunicorn)..."
GUNICORN_PATH="gunicorn"
if [ -f ".venv/bin/gunicorn" ]; then
    GUNICORN_PATH=".venv/bin/gunicorn"
fi
$GUNICORN_PATH wsgi:app --bind 0.0.0.0:${PORT:-10000} &
APP_PID=$!

# Gracefully stop all processes on Ctrl+C and SIGTERM
trap "echo 'Gracefully stopping...'; kill $APP_PID; exit" INT TERM

# Wait for the web server to finish
wait $APP_PID
