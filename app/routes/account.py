"""
Маршруты для управления аккаунтом
"""
import secrets
from datetime import datetime, timedelta

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify

from app import db
from app.models import User, TelegramLinkCode, Task
from app.utils import require_login
import logging

logger = logging.getLogger(__name__)
account_bp = Blueprint('account', __name__)

LINK_CODE_TTL_MINUTES = 15


@account_bp.route('/profile')
@require_login
def profile():
    """Личный профиль пользователя"""
    try:
        user_id = session.get('user_id')
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

    except Exception as e:
        logger.error(f"Error loading profile: {str(e)}")
        return redirect(url_for('main.index'))


@account_bp.route('/settings')
@require_login
def settings():
    """Настройки аккаунта"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        return render_template(
            'settings.html',
            user=user,
            telegram_linked=user.telegram_user_id is not None if user else False,
            link_ttl_minutes=LINK_CODE_TTL_MINUTES,
        )

    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return redirect(url_for('main.index'))


@account_bp.route('/telegram/generate-link', methods=['POST'])
@require_login
def telegram_generate_link():
    """Выдать одноразовый код привязки Telegram."""
    try:
        user_id = session.get('user_id')
        TelegramLinkCode.query.filter_by(user_id=user_id).delete()

        code = secrets.token_hex(8).upper()
        row = TelegramLinkCode(
            user_id=user_id,
            code=code,
            expires_at=datetime.utcnow() + timedelta(minutes=LINK_CODE_TTL_MINUTES),
        )
        db.session.add(row)
        db.session.commit()

        logger.info(f"Telegram link code generated for user {user_id}")
        return jsonify({
            'code': code,
            'expires_in_minutes': LINK_CODE_TTL_MINUTES,
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error generating telegram link: {str(e)}")
        return jsonify({'error': 'Ошибка при генерации кода'}), 500


@account_bp.route('/telegram/unlink', methods=['POST'])
@require_login
def telegram_unlink():
    """Отвязать Telegram от аккаунта."""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        user.telegram_user_id = None
        TelegramLinkCode.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        logger.info(f"Telegram unlinked for user {user_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unlinking telegram: {str(e)}")
        return jsonify({'error': 'Ошибка при отвязке'}), 500


@account_bp.route('/edit', methods=['POST'])
@require_login
def edit_profile():
    """Редактирование профиля"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        data = request.get_json() or request.form

        if 'email' in data:
            new_email = data['email'].strip().lower()
            if new_email != user.email:
                if User.query.filter_by(email=new_email).first():
                    return jsonify({'error': 'Этот email уже зарегистрирован'}), 409
                user.email = new_email

        db.session.commit()
        logger.info(f"Profile updated for user {user_id}")
        return jsonify({'success': True, 'message': 'Профиль обновлен'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing profile: {str(e)}")
        return jsonify({'error': 'Ошибка при редактировании профиля'}), 500
