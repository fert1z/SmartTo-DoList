"""
Маршруты аутентификации
"""
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User
from app import db
from app.utils import validate_email_format, validate_username, validate_password
from app.mail_utils import send_email
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа и обработка входа"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')

            if not username or not password:
                flash('Заполните все поля', 'error')
                return render_template('login.html'), 400

            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                session.permanent = True
                session['user_id'] = user.id
                session['username'] = user.username
                logger.info(f"User {username} logged in")
                return redirect(url_for('main.dashboard'))

            logger.warning(f"Failed login attempt for user {username}")
            flash('Неверные учетные данные', 'error')
            return render_template('login.html'), 401
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Произошла ошибка при входе', 'error')
            return render_template('login.html'), 500

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации и обработка регистрации"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Валидация полей
            if not all([username, email, password, confirm_password]):
                flash('Заполните все поля', 'error')
                return render_template('registration.html'), 400

            # Валидация username
            valid, msg = validate_username(username)
            if not valid:
                flash(msg or 'Некорректный username', 'error')
                return render_template('registration.html'), 400

            # Валидация email
            if not validate_email_format(email):
                flash('Некорректный формат email', 'error')
                return render_template('registration.html'), 400

            # Валидация пароля
            valid, msg = validate_password(password)
            if not valid:
                flash(msg or 'Некорректный пароль', 'error')
                return render_template('registration.html'), 400

            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return render_template('registration.html'), 400

            # Проверка существования пользователя
            if User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем уже существует', 'error')
                return render_template('registration.html'), 409

            if User.query.filter_by(email=email).first():
                flash('Email уже зарегистрирован', 'error')
                return render_template('registration.html'), 409

            # Создание пользователя
            user = User(username=username, email=email)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            logger.info(f"New user registered: {username}")
            flash('Регистрация успешна! Добро пожаловать!', 'success')

            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username

            return redirect(url_for('main.dashboard'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('Произошла ошибка при регистрации', 'error')
            return render_template('registration.html'), 500

    return render_template('registration.html')


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    username = session.get('username', 'Unknown')
    logger.info(f"User {username} logged out")
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Восстановление пароля"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()

            if not validate_email_format(email):
                flash('Введите корректный email', 'error')
                return render_template('forgot_password.html'), 400

            user = User.query.filter_by(email=email).first()
            if user:
                logger.info(f"Password reset requested for email: {email}")

                # В проекте пока нет механизма токенов/ссылок смены пароля.
                # Поэтому отправляем уведомление с общей инструкцией.
                subject = "SmartTo-DoList: восстановление пароля"
                body_text = (
                    "Здравствуйте!\n\n"
                    "Вы запросили восстановление пароля в SmartTo-DoList.\n\n"
                    "Перейдите в настройки аккаунта /auth/forgot-password, "
                    "чтобы завершить восстановление.\n\n"
                    "Если вы не делали запрос — просто проигнорируйте это письмо.\n"
                )

                ok = send_email(
                    to_email=email,
                    subject=subject,
                    body_text=body_text,
                )
                if ok:
                    logger.info("Password reset email sent to %s", email)
                else:
                    logger.warning("Password reset email skipped/failed for %s (SMTP not configured?)", email)

                flash('Если этот email зарегистрирован, на него будет отправлено письмо восстановления', 'info')
            else:
                flash('Если этот email зарегистрирован, на него будет отправлено письмо восстановления', 'info')

            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}")
            flash('Произошла ошибка', 'error')
            return render_template('forgot_password.html'), 500

    return render_template('forgot_password.html')
