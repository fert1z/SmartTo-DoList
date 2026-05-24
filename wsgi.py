"""
WSGI entry point для приложения SmartTo-DoList
Используется для запуска с Gunicorn или другими WSGI серверами
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / '.env')
except ImportError:
    pass

from app import create_app, db, init_db
from flask_migrate import Migrate

# Создаем приложение
app = create_app(
    config_name=os.getenv('FLASK_CONFIG') or os.getenv('FLASK_ENV') or 'production',
    scheduler_enabled=True,
)
migrate = Migrate(app, db)


@app.shell_context_processor
def make_shell_context():
    """Контекст для shell"""
    return {'db': db}


@app.cli.command()
def init_database():
    """Инициализация базы данных"""
    init_db(app)


if __name__ == '__main__':
    # Для разработки
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
