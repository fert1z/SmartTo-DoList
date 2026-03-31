"""
WSGI entry point для приложения SmartTo-DoList
Используется для запуска с Gunicorn или другими WSGI серверами
"""
import os
from app import create_app, db, init_db

# Создаем приложение
app = create_app(config_name=os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Контекст для shell"""
    return {'db': db}


@app.cli.command()
def init_database():
    """Инициализация базы данных"""
    init_db()


if __name__ == '__main__':
    # Для разработки
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000)),
        debug=os.getenv('FLASK_ENV') == 'development'
    )
