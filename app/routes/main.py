"""
Основные маршруты приложения
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models import Task
from app import db
from app.utils import require_login
import logging

logger = logging.getLogger(__name__)
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
@require_login
def dashboard():
    """Панель управления"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('error500.html'), 500


@main_bp.route('/addtask')
@require_login
def addtask():
    """Страница добавления задачи"""
    try:
        return render_template('addtask.html')
    except Exception as e:
        logger.error(f"Error loading addtask page: {str(e)}")
        return render_template('error500.html'), 500
