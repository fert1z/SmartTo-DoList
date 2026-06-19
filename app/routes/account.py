"""
Account management routes
"""
import secrets
from datetime import datetime, timedelta
import zoneinfo

from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify

from app import db
from app.models import Task, TelegramLinkCode, User
from app.utils import require_login, validate_password, validate_username
from app.limiter import limiter
import logging

logger = logging.getLogger(__name__)
account_bp = Blueprint('account', __name__)

LINK_CODE_TTL_MINUTES = 15


@account_bp.route('/profile')
@require_login
def profile():
    """User profile"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            session.clear()
            return redirect(url_for('auth.login'))

        completed = Task.query.filter_by(user_id=user_id, status='COMPLETED').count()
        active = (
            Task.query.filter_by(user_id=user_id)
            .filter(Task.status != 'COMPLETED')
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
    """Account settings"""
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
    """Issue a one-time code for linking Telegram."""
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
        return jsonify({'error': 'Error generating code'}), 500


@account_bp.route('/telegram/unlink', methods=['POST'])
@require_login
@limiter.limit('10 per hour')
def telegram_unlink():
    """Unlink Telegram from the account."""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.telegram_user_id = None
        TelegramLinkCode.query.filter_by(user_id=user_id).delete()
        db.session.commit()

        logger.debug(f"Telegram unlinked for user {user_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error unlinking telegram: {str(e)}")
        return jsonify({'error': 'Error unlinking'}), 500


@account_bp.route('/edit', methods=['POST'])
@require_login
@limiter.limit('20 per hour')
def edit_profile():
    """Edit profile"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        data = request.get_json()

        if not user:
            return jsonify({'error': 'User not found'}), 404

        current_password = data.get('current_password')
        if not current_password or not user.check_password(current_password):
            return jsonify({'error': 'Invalid current password'}), 403

        changes_made = False

        # 1. Change username
        if 'username' in data and data['username'] != user.username:
            new_username = data['username'].strip()
            is_valid, msg = validate_username(new_username)
            if not is_valid:
                return jsonify({'error': msg}), 400
            if User.query.filter(User.id != user_id, User.username == new_username).first():
                return jsonify({'error': 'This username is already taken'}), 409
            user.username = new_username
            session['username'] = new_username # Update username in session
            changes_made = True

        # 2. Change password
        if 'new_password' in data and data['new_password']:
            new_password = data['new_password']
            confirm_password = data.get('confirm_password')
            
            if new_password != confirm_password:
                return jsonify({'error': 'New passwords do not match'}), 400
            
            is_valid, msg = validate_password(new_password)
            if not is_valid:
                return jsonify({'error': msg}), 400
            
            user.set_password(new_password)
            changes_made = True

        # 3. Change timezone
        if 'timezone' in data and data['timezone'] != user.timezone:
            user.timezone = data['timezone']
            changes_made = True

        if not changes_made:
            return jsonify({'success': True, 'message': 'No changes to save.'})

        db.session.commit()
        logger.info(f"Profile updated for user {user_id}")
        return jsonify({'success': True, 'message': 'Settings saved successfully!'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error editing profile: {e}", exc_info=True)
        return jsonify({'error': 'An internal error occurred while saving'}), 500