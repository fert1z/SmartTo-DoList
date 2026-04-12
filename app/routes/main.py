"""
Основные маршруты приложения
"""
from flask import Blueprint, render_template, request, jsonify
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models import Task
from app import db

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Главная страница"""
    return render_template('main_page.html')


@main_bp.route('/about')
def about():
    """Страница О проекте"""
    return render_template('about.html')


@main_bp.route('/dashboard')
def dashboard():
    """Панель управления"""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')


@main_bp.route('/addtask')
def addtask():
    """Страница добавления задачи"""
    if not session.get('user_id'):
        return redirect(url_for('auth.login'))
    return render_template('addtask.html')
