"""
Маршруты для управления аккаунтом
"""
import secrets
from datetime import datetime, timedelta
import zoneinfo

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify

from app import db
from app.mail_utils import send_email
from app.models import EmailChangeRequest, Task, TelegramLinkCode, User
from app.utils import require_login, validate_email_format, validate_password, validate_username
from app.limiter import limiter
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
        
        timezones = sorted(list(zoneinfo.available_timezones()))

        return render_template(
            'settings.html',
            user=user,
            timezones=timezones,
            telegram_linked=user.telegram_user_id is not None if user else False,
            link_ttl_minutes=LINK_CODE_TTL_MINUTES,
        )

    except Exception as e:
        logger.error(f"Error loading settings: {str(e)}")
        return redirect(url_for('main.index'))


@account_bp.route('/telegram/generate-link', methods=['POST'])
@require_login
@limiter.limit('10 per hour')
def telegram_generate_link():
    """Выдать одноразовый код привязки Telegram."""
    try:
        user_id = session.get('user_id')
        code = secrets.token_hex(8).upper()
        
        TelegramLinkCode.query.filter_by(user_id=user_id).delete()
        
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
@limiter.limit('10 per hour')
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

        logger.debug(f"Telegram unlinked for user {user_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unlinking telegram: {str(e)}")
        return jsonify({'error': 'Ошибка при отвязке'}), 500


@account_bp.route('/edit', methods=['POST'])
@require_login
@limiter.limit('20 per hour')
def edit_profile():
    """Редактирование профиля"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        data = request.get_json()

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        current_password = data.get('current_password')
        if not current_password or not user.check_password(current_password):
            return jsonify({'error': 'Неверный текущий пароль'}), 403

        changes_made = False

        # 1. Смена имени пользователя
        if 'username' in data and data['username'] != user.username:
            new_username = data['username'].strip()
            is_valid, msg = validate_username(new_username)
            if not is_valid:
                return jsonify({'error': msg}), 400
            if User.query.filter(User.id != user_id, User.username == new_username).first():
                return jsonify({'error': 'Это имя пользователя уже занято'}), 409
            user.username = new_username
            session['username'] = new_username # Обновляем имя в сессии
            changes_made = True

        # 2. Смена Email
        if 'email' in data and data['email'].strip().lower() != user.email:
            # Логика смены email уже была, но мы ее интегрируем в общий поток
            # Для простоты, пока не будем требовать подтверждения по старому email
            new_email = data['email'].strip().lower()
            if not validate_email_format(new_email):
                return jsonify({'error': 'Некорректный email'}), 400
            if User.query.filter(User.id != user_id, User.email == new_email).first():
                return jsonify({'error': 'Этот email уже занято'}), 409
            user.email = new_email
            changes_made = True

        # 3. Смена пароля
        if 'new_password' in data and data['new_password']:
            new_password = data['new_password']
            confirm_password = data.get('confirm_password')
            
            if new_password != confirm_password:
                return jsonify({'error': 'Новые пароли не совпадают'}), 400
            
            is_valid, msg = validate_password(new_password)
            if not is_valid:
                return jsonify({'error': msg}), 400
            
            user.set_password(new_password)
            changes_made = True

        # 4. Смена часового пояса
        if 'timezone' in data and data['timezone'] != user.timezone:
            user.timezone = data['timezone']
            changes_made = True

        if not changes_made:
            return jsonify({'success': True, 'message': 'Нет изменений для сохранения.'})

        db.session.commit()
        logger.info(f"Profile updated for user {user_id}")
        return jsonify({'success': True, 'message': 'Настройки успешно сохранены!'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing profile: {str(e)}")
        return jsonify({'error': 'Произошла внутренняя ошибка при сохранении'}), 500


@account_bp.route('/confirm-email', methods=['GET'])
def confirm_email():
    token = request.args.get('token', '').strip()
    if not token:
        return redirect(url_for('account.settings'))

    request_row = EmailChangeRequest.query.filter_by(token=token, used=False).first()
    if not request_row or request_row.expires_at < datetime.utcnow():
        return redirect(url_for('account.settings'))

    user = User.query.get(request_row.user_id)
    if not user:
        return redirect(url_for('auth.login'))

    old_email = user.email
    
    user.email = request_row.new_email
    request_row.used = True
    db.session.commit()

    notification_subject = 'SmartTo-DoList: email изменён'
    notification_body = (
        'Ваш email в SmartTo-DoList был успешно обновлён.\n\n'
        'Если это были не вы, обратитесь в службу поддержки.\n'
    )
    send_email(to_email=old_email, subject=notification_subject, body_text=notification_body)

    return redirect(url_for('account.settings'))