"""
Основные маршруты приложения
"""
from flask import Blueprint, render_template, request, session, redirect, url_for
from app.routes.tasks import create_task, list_tasks, task_detail

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


@main_bp.route('/api/tasks', methods=['GET', 'POST'])
def api_tasks():
    if request.method == 'POST':
        return create_task()
    return list_tasks()


@main_bp.route('/api/tasks/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def api_task_detail(task_id):
    return task_detail(task_id)
