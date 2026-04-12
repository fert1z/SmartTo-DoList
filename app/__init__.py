from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from config import config

# Инициализация расширений
db = SQLAlchemy()


def create_app(config_name=None):
    """
    Фабрика приложения Flask
    
    Args:
        config_name (str): имя конфигурации (development, production, testing)
    
    Returns:
        Flask: экземпляр приложения Flask
    """
    # Определяем конфигурацию
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    app.config.from_object(config.get(config_name, config['default']))
    
    # Инициализируем расширения
    db.init_app(app)
    
    # Регистрируем контекст приложения для работы с БД
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db}
    
    # Регистрируем blueprints
    from app.routes import main_bp, auth_bp, tasks_bp, account_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(account_bp, url_prefix='/account')
    
    # Обработчик ошибок 404
    @app.errorhandler(404)
    def not_found(error):
        from flask import render_template
        return render_template('error404.html'), 404
    
    # Обработчик ошибок 500
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        from flask import render_template
        return render_template('error500.html'), 500
    
    with app.app_context():
        from app import models  # noqa: F401 — регистрация моделей
        db.create_all()
        from app.db_schema import apply_schema_migrations
        apply_schema_migrations(db)
    
    return app


def init_db():
    """Инициализация базы данных (схема поднимается внутри create_app)."""
    create_app()
    print("✓ База данных инициализирована")
