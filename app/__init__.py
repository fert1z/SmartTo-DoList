from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
import os
import logging
from config import config
from app.limiter import limiter

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
        config_name = os.getenv('FLASK_CONFIG') or os.getenv('FLASK_ENV') or 'production'
    
    app = Flask(__name__)
    
    # Загружаем конфигурацию
    app.config.from_object(config.get(config_name, config['default']))

    # В production SECRET_KEY должен быть задан явно
    if app.config['ENV'] == 'production' and not app.config.get('SECRET_KEY'):
        raise RuntimeError('SECRET_KEY must be set in production environment')

    # Инициализируем логирование
    from app.logging_config import setup_logging
    setup_logging(app)
    
    # Переопределяем настройку планировщика, если указано
    if scheduler_enabled is not None:
        app.config['SCHEDULER_ENABLED'] = scheduler_enabled
    
    # Инициализируем расширения
    db.init_app(app)
    csrf.init_app(app)
    if app.config.get('RATELIMIT_ENABLED', True):
        limiter.init_app(app)
    
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
        # В шаблонах HTML нужно значение токена для meta и формы.
        return {
            'csrf_token': generate_csrf,
            'csrf_token_value': generate_csrf(),
        }

    @app.after_request
    def apply_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
        response.headers['Permissions-Policy'] = 'geolocation=()'
        response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none';"
        )
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
        if app.config['ENV'] != 'production':
            # В разработке и тестах создаём таблицы и применяем упрощённые миграции.
            db.create_all()
            from app.db_schema import apply_schema_migrations
            apply_schema_migrations(db)
        else:
            app.logger.info(
                'Production database schema management must be handled externally. '
                'Skipping create_all() and schema migrations.'
            )

        # Планировщик запускается только в основном процессе, не в каждом worker'е Gunicorn.
        if app.config.get('SCHEDULER_ENABLED', True):
            is_gunicorn = os.environ.get('GUNICORN_WORKER_ID') is not None
            is_werkzeug_main = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'
            if not is_gunicorn and (not app.debug or is_werkzeug_main):
                from app.scheduler import init_scheduler
                init_scheduler(app)
            elif is_gunicorn:
                app.logger.info('Scheduler disabled in Gunicorn worker process.')

    return app


def init_db(app):
    """Инициализация базы данных."""
    with app.app_context():
        db.create_all()
        from app.db_schema import apply_schema_migrations
        apply_schema_migrations(db)
        print("✓ База данных инициализирована")
