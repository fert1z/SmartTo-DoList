"""
Маршруты аутентификации
"""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import User, PasswordResetToken, EmailConfirmationToken
from app import db
from app.limiter import limiter
from app.utils import validate_email_format, validate_username, validate_password
from app.mail_utils import send_email
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def _send_confirmation_email(user):
    """Отправляет письмо для подтверждения email."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # Удаляем старые токены для этого пользователя
    EmailConfirmationToken.query.filter_by(user_id=user.id).delete()
    
    conf_token = EmailConfirmationToken(
        user_id=user.id,
        token=token,
        expires_at=expires_at
    )
    db.session.add(conf_token)
    db.session.commit()
    
    confirm_url = url_for('auth.confirm_email', token=token, _external=True)
    subject = 'Подтвердите ваш аккаунт SmartTo-DoList'
    body_text = f"Добро пожаловать! Пожалуйста, подтвердите ваш email, перейдя по ссылке: {confirm_url}"
    
    send_email(to_email=user.email, subject=subject, body_text=body_text)


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
                if not user.is_email_confirmed:
                    flash('Ваш email не подтвержден. Пожалуйста, проверьте свою почту или запросите новое письмо.', 'warning')
                    return redirect(url_for('auth.resend_confirmation'))

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
def register():
    """Страница регистрации и обработка регистрации"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not all([username, email, password, confirm_password]):
                flash('Заполните все поля', 'error')
                return render_template('registration.html'), 400

            valid, msg = validate_username(username)
            if not valid:
                flash(msg, 'error')
                return render_template('registration.html'), 400

            if not validate_email_format(email):
                flash('Некорректный формат email', 'error')
                return render_template('registration.html'), 400

            valid, msg = validate_password(password)
            if not valid:
                flash(msg, 'error')
                return render_template('registration.html'), 400

            if password != confirm_password:
                flash('Пароли не совпадают', 'error')
                return render_template('registration.html'), 400

            if User.query.filter((User.username == username) | (User.email == email)).first():
                flash('Пользователь с таким именем или email уже существует', 'error')
                return render_template('registration.html'), 400

            user = User(username=username, email=email, is_email_confirmed=False)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()

            _send_confirmation_email(user)

            logger.info(f"New user registered, confirmation sent to {email}")
            flash('Регистрация почти завершена! Мы отправили письмо с подтверждением на ваш email.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
            logger.error(f"Registration error: {str(e)}")
            flash('Произошла ошибка при регистрации', 'error')
            return render_template('registration.html'), 500

    return render_template('registration.html')


@auth_bp.route('/confirm/<token>')
def confirm_email(token):
    """Обработка токена подтверждения email."""
    conf_token = EmailConfirmationToken.query.filter_by(token=token, used=False).first()
    
    if conf_token and conf_token.expires_at > datetime.utcnow():
        user = User.query.get(conf_token.user_id)
        if user:
            user.is_email_confirmed = True
            user.email_confirmed_at = datetime.utcnow()
            conf_token.used = True
            db.session.commit()
            flash('Ваш email успешно подтвержден! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))

    flash('Ссылка для подтверждения недействительна или истекла.', 'error')
    return redirect(url_for('auth.login'))


@auth_bp.route('/resend-confirmation', methods=['GET', 'POST'])
def resend_confirmation():
    """Повторная отправка письма с подтверждением."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            if user.is_email_confirmed:
                flash('Этот email уже подтвержден.', 'info')
                return redirect(url_for('auth.login'))
            
            _send_confirmation_email(user)
            flash('Новое письмо с подтверждением отправлено.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Пользователь с таким email не найден.', 'error')

    return render_template('resend_confirmation.html')


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    logger.info(f"User logged out")
    session.clear()
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('main.index'))


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

            user = User.query.filter_by(email=email).first()
            if user:
                token = secrets.token_urlsafe(32)
                expires_at = datetime.utcnow() + timedelta(hours=1)
                
                PasswordResetToken.query.filter_by(user_id=user.id).delete()
                reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
                db.session.add(reset_token)
                db.session.commit()

                reset_url = url_for('auth.reset_password', token=token, _external=True)
                subject = 'SmartTo-DoList: восстановление пароля'
                body_text = f"Для сброса пароля перейдите по ссылке: {reset_url}"
                send_email(to_email=email, subject=subject, body_text=body_text)

            flash('Если этот email зарегистрирован, на него будет отправлено письмо для сброса пароля.', 'info')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.session.rollback()
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
            flash(msg, 'error')
            return render_template('reset_password.html', token=token), 400

        user = User.query.get(reset_token.user_id)
        if not user:
            flash('Пользователь не найден', 'error')
            return redirect(url_for('auth.forgot_password'))

        user.set_password(password)
        reset_token.used = True
        db.session.commit()

        flash('Пароль успешно сброшен. Войдите в систему с новым паролем.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token)