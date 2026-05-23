"""
Маршруты аутентификации
"""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, PasswordResetToken
from app import db
from app.limiter import limiter
from app.utils import validate_email_format, validate_username, validate_password
from app.mail_utils import send_email
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per 15 minutes")  # Защита от brute-force: 5 попыток в 15 минут
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
                # Защита от session fixation: очищаем сессию перед установкой новых значений
                session.clear()
                session.permanent = True
                session['user_id'] = user.id
                session['username'] = user.username
                logger.info(f"User login successful")
                return redirect(url_for('main.dashboard'))

            logger.warning(f"Failed login attempt")
            flash('Неверные учетные данные', 'error')
            return render_template('login.html'), 401
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('Произошла ошибка при входе', 'error')
            return render_template('login.html'), 500

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit("3 per hour")  # Защита от brute-force регистрации: 3 попытки в час
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

            # Проверка существования пользователя (generic сообщение для защиты от перечисления аккаунтов)
            if User.query.filter_by(username=username).first():
                flash('Пользователь с таким именем или email уже существует', 'error')
                return render_template('registration.html'), 400

            if User.query.filter_by(email=email).first():
                flash('Пользователь с таким именем или email уже существует', 'error')
                return render_template('registration.html'), 400

            # Создание пользователя
            user = User(username=username, email=email)
            user.set_password(password)

            db.session.add(user)
            db.session.commit()

            logger.info(f"New user registered")
            flash('Регистрация успешна! Добро пожаловать!', 'success')

            # Защита от session fixation: очищаем сессию перед установкой новых значений
            session.clear()
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
    logger.info(f"User logged out")
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('main.index'))


def _cleanup_expired_reset_tokens() -> None:
    with db.session.begin():
        PasswordResetToken.query.filter(PasswordResetToken.expires_at < datetime.utcnow()).delete(synchronize_session=False)


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password():
    """Восстановление пароля"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()

            if not validate_email_format(email):
                flash('Введите корректный email', 'error')
                return render_template('forgot_password.html'), 400

            _cleanup_expired_reset_tokens()
            user = User.query.filter_by(email=email).first()
            if user:
                logger.info("Password reset requested for user_id=%s", user.id)

                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=1)
                with db.session.begin():
                    PasswordResetToken.query.filter_by(user_id=user.id).delete(synchronize_session=False)
                    reset_token = PasswordResetToken(
                        user_id=user.id,
                        token=token,
                        expires_at=expires_at,
                        used=False,
                    )
                    db.session.add(reset_token)

                reset_url = url_for('auth.reset_password', token=token, _external=True)
                subject = 'SmartTo-DoList: восстановление пароля'
                body_text = (
                    f'Здравствуйте!\n\n'
                    f'Вы запросили восстановление пароля для аккаунта SmartTo-DoList.\n\n'
                    f'Перейдите по ссылке, чтобы сбросить пароль:\n{reset_url}\n\n'
                    'Ссылка действительна 1 час. Если вы не делали этот запрос, просто проигнорируйте это письмо.\n'
                )

                ok = send_email(
                    to_email=email,
                    subject=subject,
                    body_text=body_text,
                )
                if ok:
                    logger.info('Password reset email queued for user_id=%s', user.id)
                else:
                    logger.warning('Password reset email skipped/failed for user_id=%s (SMTP not configured?)', user.id)

            flash('Если этот email зарегистрирован, на него будет отправлено письмо восстановления', 'info')
            return redirect(url_for('auth.login'))

        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}")
            flash('Произошла ошибка', 'error')
            return render_template('forgot_password.html'), 500

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Сброс пароля по одноразовому токену."""
    token = request.args.get('token') if request.method == 'GET' else request.form.get('token')
    if not token:
        flash('Недействительная или отсутствующая ссылка для сброса пароля', 'error')
        return redirect(url_for('auth.forgot_password'))

    _cleanup_expired_reset_tokens()
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not reset_token or reset_token.expires_at < datetime.utcnow():
        flash('Ссылка для сброса пароля недействительна или истекла', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('reset_password.html', token=token), 400

        valid, msg = validate_password(password)
        if not valid:
            flash(msg or 'Некорректный пароль', 'error')
            return render_template('reset_password.html', token=token), 400

        user = User.query.get(reset_token.user_id)
        if not user:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('auth.forgot_password'))

        with db.session.begin():
            user.set_password(password)
            reset_token.used = True

        notification_subject = 'SmartTo-DoList: пароль был изменён'
        notification_body = (
            'Пароль для вашего аккаунта SmartTo-DoList был успешно изменён.\n\n'
            'Если это были не вы, немедленно обратитесь в службу поддержки и сбросьте пароль снова.\n'
        )
        if send_email(to_email=user.email, subject=notification_subject, body_text=notification_body):
            logger.info('Password reset notification sent to user_id=%s', user.id)
        else:
            logger.warning('Password reset notification failed for user_id=%s', user.id)

        flash('Пароль успешно сброшен. Войдите в систему с новым паролем.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)
