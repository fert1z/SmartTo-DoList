"""
Маршруты для управления аккаунтом
"""
from flask import Blueprint, render_template, session, redirect, url_for, request, jsonify

account_bp = Blueprint('account', __name__)


@account_bp.route('/profile')
def profile():
    """Личный профиль пользователя"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    return render_template('account.html')


@account_bp.route('/settings')
def settings():
    """Настройки аккаунта"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))
    
    return render_template('settings.html')


@account_bp.route('/edit', methods=['POST'])
def edit_profile():
    """Редактирование профиля"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401
    
    # TODO: Реализовать редактирование профиля
    return jsonify({'success': True})
