"""Утилиты для валидации и аутентификации"""
import re
from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from email_validator import validate_email, EmailNotValidError


def validate_email_format(email):
    """Валидирует формат email"""
    try:
        validate_email(email, check_deliverability=False)
        return True
    except EmailNotValidError:
        return False


def validate_username(username):
    """Валидирует username - от 3 до 20 символов, буквы, цифры, подчеркивание"""
    if not username:
        return False, "Username обязателен"
    if len(username) < 3:
        return False, "Username должен быть не менее 3 символов"
    if len(username) > 20:
        return False, "Username не должен превышать 20 символов"
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username может содержать только буквы, цифры и подчеркивание"
    return True, None


def validate_password(password):
    """Валидирует пароль"""
    if not password:
        return False, "Пароль обязателен"
    if len(password) < 8:
        return False, "Пароль должен быть не менее 8 символов"
    if len(password) > 128:
        return False, "Пароль не должен превышать 128 символов"
    return True, None


def require_login(f):
    """Декоратор для проверки аутентификации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            if request.is_json or request.path.startswith('/api'):
                return jsonify({'error': 'Не авторизован'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function
