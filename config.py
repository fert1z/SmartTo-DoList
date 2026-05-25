import os
from datetime import timedelta

class Config:
    """Базовая конфигурация приложения"""
    # Flask
    DEBUG = False
    ENV = 'production'
    TESTING = False
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    
    # Безопасность
    SECRET_KEY = os.environ.get('SECRET_KEY')
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    MAIL_REQUIRE_AUTH = os.environ.get('MAIL_REQUIRE_AUTH', '1').strip().lower() in ('1', 'true', 'yes', 'y', 'on')
    
    # Телеграм
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    TELEGRAM_API_URL = 'https://api.telegram.org'

    # Почта для восстановления пароля
    MAIL_SERVER = os.environ.get('MAIL_SERVER', '')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', '1').lower() in ('1', 'true', 'yes')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'no-reply@smarttodolist.local')
    
    # ИИ функции (опционально)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')

    # Пагинация
    ITEMS_PER_PAGE = 10

    # Планировщик напоминаний
    SCHEDULER_ENABLED = True
    REMINDER_INTERVAL_MINUTES = 5
    REMINDER_LOOKAHEAD_MINUTES = 15

    # Максимальный размер файла (5MB)
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024


class DevelopmentConfig(Config):
    """Конфигурация для разработки"""
    DEBUG = True
    ENV = 'development'
    TESTING = False
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    SECRET_KEY = 'dev-secret-key-change-in-development'
    
    # Base directory
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DEV_DATABASE_URL',
        'sqlite:///' + os.path.join(BASEDIR, 'instance', 'users.db')
    )


class ProductionConfig(Config):
    """Конфигурация для продакшена"""
    DEBUG = False
    ENV = 'production'
    TESTING = False
    SESSION_COOKIE_SECURE = True

    # Database - поддержка как старого, так и нового формата PostgreSQL
    _db_url = os.environ.get('DATABASE_URL', '')
    if _db_url:
        # Убеждаемся, что используется правильный драйвер psycopg3
        if _db_url.startswith('postgres://'):
            _db_url = _db_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif _db_url.startswith('postgresql://'):
            _db_url = _db_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        # Если DATABASE_URL не установлен, использовать SQLite
        BASEDIR = os.path.abspath(os.path.dirname(__file__))
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            'DATABASE_URL',
            'sqlite:///' + os.path.join(BASEDIR, 'instance', 'users.db')
        )


class TestingConfig(Config):
    """Конфигурация для тестирования"""
    DEBUG = True
    TESTING = True
    SECRET_KEY = 'testing-secret-key'
    
    # Database для тестов (в памяти)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False  # Отключить rate limiting при тестировании


# Выбор конфигурации в зависимости от окружения
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}