from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
import os
import logging
from config import config
from flask_wtf.csrf import CSRFProtect, generate_csrf

# Инициализация расширений
db = SQLAlchemy()
csrf = CSRFProtect()


def create_app(config_name=None, scheduler_enabled=None):
    """
    Фабрика приложения Flask
    
    Args:
        config_name (str): имя конфигурации (development, production, testing)
        scheduler_enabled (bool): включить ли планировщик (по умолчанию True)
    
    Returns:
        Flask: экземпляр приложения Flask
    """
    # Определяем конфигурацию
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    app.config.from_object(config.get(config_name, config['default']))

    # Инициализируем логирование
    from app.logging_config import setup_logging
    setup_logging(app)
    
    # Переопределяем настройку планировщика, если указано
    if scheduler_enabled is not None:
        app.config['SCHEDULER_ENABLED'] = scheduler_enabled
    
    # Инициализируем расширения
    db.init_app(app)
    csrf.init_app(app)
    
    # Регистрируем контекст приложения для работы с БД
    @app.shell_context_processor
    def make_shell_context():
        return {'db': db}
    
    # Регистрируем blueprints
    from app.routes import main_bp, auth_bp, tasks_bp, account_bp
    
    # REST API под /api/tasks
    from app.routes.api_tasks import api_tasks_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(tasks_bp, url_prefix='/tasks')
    app.register_blueprint(api_tasks_bp)
    app.register_blueprint(account_bp, url_prefix='/account')

    @app.context_processor
    def inject_csrf_token():
        return {'csrf_token': generate_csrf()}

    @app.after_request
    def apply_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
        response.headers['Permissions-Policy'] = 'geolocation=()'
        return response

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
        # Применяем легкие миграции для обновления схемы БД (добавление новых колонок)
        from app.db_schema import apply_schema_migrations
        apply_schema_migrations(db)

        # Запускаем планировщик уведомлений только в основном процессе
        if app.config.get('SCHEDULER_ENABLED', True) and (
            not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
        ):
            from app.scheduler import init_scheduler
            init_scheduler(app)

    return app


def init_db(app):
    """Инициализация базы данных."""
    with app.app_context():
        db.create_all()
        from app.db_schema import apply_schema_migrations
        apply_schema_migrations(db)
        print("✓ База данных инициализирована")
