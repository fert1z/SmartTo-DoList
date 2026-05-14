"""
Маршруты аутентификации
"""
import secrets
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
import threading

from flask import Blueprint, render_template, request, redirect, url_for, session, current_app
from app.models import User, PasswordResetToken
from app import db
import re

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа и обработка входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Заполните все поля')
        
        user = User.query.filter(User.username.ilike(username)).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', error='Неверные учетные данные')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации и обработка регистрации"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Валидация
        if not all([username, email, password, confirm_password]):
            return render_template('registration.html', error='Заполните все поля')
        
        if password != confirm_password:
            return render_template('registration.html', error='Пароли не совпадают')
        
        if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
            return render_template('registration.html', error='Имя пользователя должно быть от 3 до 20 символов (латиница и цифры)')

        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return render_template('registration.html', error='Некорректный формат email')

        if len(password) < 8:
            return render_template('registration.html', error='Пароль должен быть не менее 8 символов')
        
        if User.query.filter(User.username.ilike(username)).first():
            return render_template('registration.html', error='Пользователь уже существует')
        
        if User.query.filter(User.email.ilike(email)).first():
            return render_template('registration.html', error='Email уже зарегистрирован')
        
        # Создаем нового пользователя
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('registration.html')


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('main.index'))


def _send_email_async(app, subject, recipient, body):
    with app.app_context():
        _send_email_sync(subject, recipient, body)

def _send_email_sync(subject, recipient, body):
    mail_server = current_app.config.get('MAIL_SERVER')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
    mail_username = current_app.config.get('MAIL_USERNAME')
    mail_password = current_app.config.get('MAIL_PASSWORD')
    mail_sender = current_app.config.get('MAIL_DEFAULT_SENDER', 'no-reply@smarttodolist.local')

    if not mail_server:
        current_app.logger.warning('Mail server is not configured. Email content:\n%s', body)
        print('Email to', recipient)
        print(body)
        return

    message = EmailMessage()
    message['Subject'] = subject
    message['From'] = mail_sender
    message['To'] = recipient
    message.set_content(body)

    try:
        with smtplib.SMTP(mail_server, mail_port, timeout=10) as smtp:
            if mail_use_tls:
                smtp.starttls()
            if mail_username and mail_password:
                smtp.login(mail_username, mail_password)
            smtp.send_message(message)
    except Exception as error:
        current_app.logger.exception('Не удалось отправить письмо: %s', error)
        raise

def _send_email(subject, recipient, body):
    """Асинхронная отправка почты, чтобы не блокировать интерфейс"""
    app = current_app._get_current_object()
    threading.Thread(target=_send_email_async, args=(app, subject, recipient, body)).start()


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Восстановление пароля"""
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        if not email:
            return render_template('forgot_password.html', error='Введите корректный email')

        user = User.query.filter_by(email=email).first()
        user = User.query.filter(User.email.ilike(email)).first()
        if user:
            PasswordResetToken.query.filter_by(user_id=user.id, used=False).delete()
            token = secrets.token_urlsafe(24)
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                used=False,
            )
            db.session.add(reset_token)
            db.session.commit()

            reset_link = url_for('auth.reset_password', token=token, _external=True)
            body = (
                f'Здравствуйте, {user.username}!\n\n'
                'Мы получили запрос на восстановление пароля. Перейдите по ссылке, чтобы задать новый пароль:\n\n'
                f'{reset_link}\n\n'
                'Если вы не запрашивали сброс пароля, просто проигнорируйте это сообщение.'
            )
            try:
                _send_email('Сброс пароля SmartTo-DoList', user.email, body)
            except Exception:
                current_app.logger.warning('Сбой отправки письма сброса пароля, но продолжим.')

        return render_template(
            'forgot_password.html',
            success='Если указанный email зарегистрирован, на него отправлена ссылка для сброса пароля.',
        )

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Сброс пароля по токену"""
    token = request.values.get('token', '').strip()
    if request.method == 'GET':
        if not token:
            return render_template('reset_password.html', error='Неверный или просроченный токен.')

        token_row = PasswordResetToken.query.filter_by(token=token, used=False).first()
        if not token_row or token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            return render_template('reset_password.html', error='Токен недействителен или устарел.')

        return render_template('reset_password.html', token=token)

    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not token:
        return render_template('reset_password.html', error='Неверный или просроченный токен.')

    token_row = PasswordResetToken.query.filter_by(token=token, used=False).first()
    if not token_row or token_row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        return render_template('reset_password.html', error='Токен недействителен или устарел.')

    if not password or len(password) < 8:
        return render_template('reset_password.html', token=token, error='Пароль должен содержать не менее 8 символов.')
    if password != confirm_password:
        return render_template('reset_password.html', token=token, error='Пароли не совпадают.')

    user = User.query.get(token_row.user_id)
    if not user:
        return render_template('reset_password.html', error='Пользователь не найден.')

    user.set_password(password)
    token_row.used = True
    db.session.commit()

    return render_template(
        'reset_password.html',
        success='Пароль успешно сброшен. Теперь войдите с новым паролем.',
    )
