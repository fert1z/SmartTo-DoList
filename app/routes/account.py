"""
Маршруты для управления аккаунтом
"""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify

from app import db
from app.models import User, TelegramLinkCode, Task

account_bp = Blueprint('account', __name__)

LINK_CODE_TTL_MINUTES = 15


@account_bp.route('/profile')
def profile():
    """Личный профиль пользователя"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    completed = Task.query.filter_by(user_id=user_id, status='completed').count()
    active = (
        Task.query.filter_by(user_id=user_id)
        .filter(Task.status != 'completed')
        .count()
    )

    return render_template(
        'account.html',
        user=user,
        stats={'completed': completed, 'active': active},
        telegram_linked=bool(user.telegram_user_id),
    )


@account_bp.route('/settings')
def settings():
    """Настройки аккаунта"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    return render_template(
        'settings.html',
        user=user,
        telegram_linked=user.telegram_user_id is not None if user else False,
        link_ttl_minutes=LINK_CODE_TTL_MINUTES,
    )


@account_bp.route('/telegram/generate-link', methods=['POST'])
def telegram_generate_link():
    """Выдать одноразовый код привязки Telegram."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401

    TelegramLinkCode.query.filter_by(user_id=user_id).delete()
    code = secrets.token_hex(4).upper()
    row = TelegramLinkCode(
        user_id=user_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=LINK_CODE_TTL_MINUTES),
    )
    db.session.add(row)
    db.session.commit()

    return jsonify({
        'code': code,
        'expires_in_minutes': LINK_CODE_TTL_MINUTES,
    })


@account_bp.route('/telegram/unlink', methods=['POST'])
def telegram_unlink():
    """Отвязать Telegram от аккаунта."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user.telegram_user_id = None
    TelegramLinkCode.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({'success': True})


@account_bp.route('/edit', methods=['POST'])
def edit_profile():
    """Редактирование профиля"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    username = (request.form.get('username') or '').strip()
    email = (request.form.get('email') or '').strip().lower()
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not username or not email:
        return render_template(
            'settings.html',
            user=user,
            telegram_linked=bool(user.telegram_user_id),
            link_ttl_minutes=LINK_CODE_TTL_MINUTES,
            error='Имя пользователя и email обязательны.',
        )

    if User.query.filter(User.username == username, User.id != user.id).first():
        return render_template(
            'settings.html',
            user=user,
            telegram_linked=bool(user.telegram_user_id),
            link_ttl_minutes=LINK_CODE_TTL_MINUTES,
            error='Имя пользователя уже занято.',
        )

    if User.query.filter(User.email == email, User.id != user.id).first():
        return render_template(
            'settings.html',
            user=user,
            telegram_linked=bool(user.telegram_user_id),
            link_ttl_minutes=LINK_CODE_TTL_MINUTES,
            error='Email уже используется другим аккаунтом.',
        )

    if new_password or confirm_password:
        if not current_password or not user.check_password(current_password):
            return render_template(
                'settings.html',
                user=user,
                telegram_linked=bool(user.telegram_user_id),
                link_ttl_minutes=LINK_CODE_TTL_MINUTES,
                error='Введите текущий пароль для изменения пароля.',
            )
        if new_password != confirm_password:
            return render_template(
                'settings.html',
                user=user,
                telegram_linked=bool(user.telegram_user_id),
                link_ttl_minutes=LINK_CODE_TTL_MINUTES,
                error='Новый пароль и подтверждение не совпадают.',
            )
        if len(new_password) < 8:
            return render_template(
                'settings.html',
                user=user,
                telegram_linked=bool(user.telegram_user_id),
                link_ttl_minutes=LINK_CODE_TTL_MINUTES,
                error='Пароль должен содержать не менее 8 символов.',
            )
        user.set_password(new_password)

    user.username = username
    user.email = email
    db.session.commit()
    session['username'] = user.username

    return render_template(
        'settings.html',
        user=user,
        telegram_linked=bool(user.telegram_user_id),
        link_ttl_minutes=LINK_CODE_TTL_MINUTES,
        success='Профиль обновлён успешно.',
    )
