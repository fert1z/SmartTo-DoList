"""Конфигурация логирования приложения"""
import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(app):
    """Настраивает логирование для приложения"""
    log_dir = Path(app.instance_path) / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        os.chmod(log_dir, 0o700)
    except OSError:
        pass

    # Создаем форматер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Обработчик для файла (все логи)
    app_log = log_dir / 'app.log'
    app_log.touch(exist_ok=True)
    try:
        os.chmod(app_log, 0o600)
    except OSError:
        pass
    file_handler = logging.handlers.RotatingFileHandler(
        app_log,
        maxBytes=10485760,
        backupCount=10
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Обработчик для ошибок
    error_log = log_dir / 'error.log'
    error_log.touch(exist_ok=True)
    try:
        os.chmod(error_log, 0o600)
    except OSError:
        pass
    error_handler = logging.handlers.RotatingFileHandler(
        error_log,
        maxBytes=10485760,
        backupCount=10
    )
    error_handler.setFormatter(formatter)
    error_handler.setLevel(logging.ERROR)

    # Обработчик консоли (только для разработки)
    if app.debug:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        app.logger.addHandler(console_handler)

    # Добавляем обработчики
    app.logger.addHandler(file_handler)
    app.logger.addHandler(error_handler)
    app.logger.setLevel(logging.INFO)

    # Настраиваем логирование для модулей
    logging.getLogger('app').addHandler(file_handler)
    logging.getLogger('app').addHandler(error_handler)
    logging.getLogger('app').setLevel(logging.INFO)

    return app.logger
