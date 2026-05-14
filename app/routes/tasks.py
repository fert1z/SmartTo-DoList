"""
Маршруты для работы с задачами
"""
from datetime import datetime, timedelta, timezone
import re
from threading import Thread

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app
from sqlalchemy import or_
from app.models import Task, User
from app import db
from app.utils import (
    parse_due_date,
    format_datetime_for_user,
    suggest_task_priority,
    infer_task_category,
)

tasks_bp = Blueprint('tasks', __name__)


def update_task_ai(task_id, app):
    """Update task priority and category using AI in background."""
    with app.app_context():
        task = Task.query.get(task_id)
        if task:
            try:
                updated = False
                if task.priority == 'medium':
                    task.priority = suggest_task_priority(task.title, task.description)
                    updated = True
                if task.category == 'personal':
                    task.category = infer_task_category(task.title, task.description)
                    updated = True
                if updated:
                    db.session.commit()
            except Exception as e:
                app.logger.warning(f"Failed to update task {task_id} with AI: {e}")


@tasks_bp.route('/new', methods=['GET', 'POST'])
def create_task():
    """Создание новой задачи"""
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 401

        title = request.form.get('task-title')
        description = request.form.get('task-description')
        due_date = request.form.get('task-datetime')
        priority = request.form.get('priority', 'medium')
        category = request.form.get('category', 'personal')
        
        if not title or not title.strip():
            return jsonify({'error': 'Название задачи обязательно'}), 400

        due_dt = parse_due_date(due_date, user.timezone or 'UTC')
        if due_date and str(due_date).strip() and due_dt is None:
            return jsonify({'error': 'Некорректная дата и время'}), 400

        task = Task(
            title=title,
            description=description,
            due_date=due_dt,
            priority=priority,
            category=category,
            user_id=user_id,
        )
        
        db.session.add(task)
        db.session.commit()
        
        # Update priority and category with AI in background if defaults were used
        if priority == 'medium' or category == 'personal':
            Thread(target=update_task_ai, args=(task.id, current_app._get_current_object())).start()
        
        return jsonify({'success': True, 'task_id': task.id})
    
    return render_template('addtask.html')


@tasks_bp.route('/list', methods=['GET'])
def list_tasks():
    """Получение списка задач пользователя"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 401

    page = max(1, int(request.args.get('page', 1) or 1))
    category = request.args.get('category', 'all')
    status = request.args.get('status', 'active')
    query = request.args.get('q', '').strip()
    per_page = current_app.config.get('ITEMS_PER_PAGE', 10)

    task_query = Task.query.filter_by(user_id=user_id)
    if status == 'active':
        task_query = task_query.filter(Task.status != 'completed')
    elif status == 'done':
        task_query = task_query.filter(Task.status == 'completed')

    if category and category != 'all':
        task_query = task_query.filter(Task.category == category)

    if query:
        task_query = task_query.filter(
            or_(Task.title.ilike(f'%{query}%'), Task.description.ilike(f'%{query}%'))
        )

    pagination = (
        task_query.order_by(Task.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    
    tasks = pagination.items
    total_tasks = pagination.total
    pages = pagination.pages

    now = datetime.now(timezone.utc)
    tasks_data = []
    for task in tasks:
        due_date = task.due_date
        due_date_iso = format_datetime_for_user(due_date, user.timezone or 'UTC') if due_date else None
        is_overdue = task.is_overdue()
        due_in_seconds = None
        urgency = 'normal'
        if due_date:
            due_date_utc = due_date if due_date.tzinfo else due_date.replace(tzinfo=timezone.utc)
            due_in_seconds = int((due_date_utc - now).total_seconds())
            if is_overdue:
                urgency = 'overdue'
            elif due_in_seconds <= 3600:
                urgency = 'imminent'
            elif due_in_seconds <= 86400:
                urgency = 'soon'

        tasks_data.append({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'status': task.status,
            'due_date': due_date_iso,
            'category': task.category,
            'is_overdue': is_overdue,
            'urgency': urgency,
            'due_in_seconds': due_in_seconds,
        })

    return jsonify({
        'tasks': tasks_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total_tasks,
            'pages': pages,
        },
        'filters': {
            'status': status,
            'category': category,
            'query': query,
        },
    })


@tasks_bp.route('/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
def task_detail(task_id):
    """Получение, обновление или удаление задачи"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401
    
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return jsonify({'error': 'Задача не найдена'}), 404
    
    if request.method == 'GET':
        return jsonify({
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'priority': task.priority,
            'status': task.status,
            'due_date': format_datetime_for_user(task.due_date, task.owner.timezone if (task.owner and task.owner.timezone) else 'UTC') if task.due_date else None,
            'category': task.category,
        })
    
    elif request.method == 'PUT':
        data = request.get_json() or request.form

        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'priority' in data:
            if data['priority'] in ['low', 'medium', 'high']:
                task.priority = data['priority']
        if 'status' in data:
            if data['status'] in ['pending', 'in_progress', 'completed']:
                task.status = data['status']
                if task.status == 'completed' and task.completed_at is None:
                    task.complete()
        if 'due_date' in data:
            due_dt = parse_due_date(data['due_date'], task.owner.timezone if (task.owner and task.owner.timezone) else 'UTC')
            if data.get('due_date') and str(data.get('due_date')).strip() and due_dt is None:
                return jsonify({'error': 'Некорректная дата'}), 400
            task.due_date = due_dt
            task.notified_at = None
        if 'category' in data:
            task.category = data['category']

        title_changed = 'title' in data
        desc_changed = 'description' in data

        db.session.commit()
        
        # If title or description changed and priority is default, update with AI in background
        if (title_changed or desc_changed) and task.priority == 'medium':
            Thread(target=update_task_ai, args=(task.id, current_app._get_current_object())).start()
        
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({'success': True})


@tasks_bp.route('/clear-completed', methods=['POST'])
def clear_completed_tasks():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401
    deleted = Task.query.filter_by(user_id=user_id, status='completed').delete()
    db.session.commit()
    return jsonify({'success': True, 'deleted': deleted})


@tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """Отметить задачу как выполненную"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401
    
    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return jsonify({'error': 'Задача не найдена'}), 404
    
    task.complete()
    db.session.commit()
    
    return jsonify({'success': True})


@tasks_bp.route('/<int:task_id>/edit', methods=['GET'])
def edit_task(task_id):
    """Страница редактирования задачи"""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.login'))

    task = Task.query.filter_by(id=task_id, user_id=user_id).first()
    if not task:
        return render_template('error404.html'), 404

    return render_template('edit_task.html', task=task)
