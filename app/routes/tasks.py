"""
Маршруты для работы с задачами
"""
from datetime import datetime, timedelta
import re

from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models import Task, User
from app import db

tasks_bp = Blueprint('tasks', __name__)


def _parse_due_date(raw):
    """Парсинг значения datetime-local, ISO или простой естественный язык."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()

    # Поддерживаем простые фразы на русском языке.
    normalized = s.lower().replace('ё', 'е').strip()
    now = datetime.utcnow()
    if normalized.startswith('сегодня'):
        time_part = normalized.replace('сегодня', '').strip()
        due = now
        if not time_part:
            return due
        s = f'{due.date().isoformat()} {time_part}'
    elif normalized.startswith('завтра'):
        time_part = normalized.replace('завтра', '').strip()
        due = now + timedelta(days=1)
        if not time_part:
            return due
        s = f'{due.date().isoformat()} {time_part}'
    elif normalized.startswith('послезавтра'):
        time_part = normalized.replace('послезавтра', '').strip()
        due = now + timedelta(days=2)
        if not time_part:
            return due
        s = f'{due.date().isoformat()} {time_part}'
    elif normalized.startswith('через'):
        match = re.match(r'через\s*(\d+)\s*(дней|дня|часов|часа|минут|минуты)', normalized)
        if match:
            amount = int(match.group(1))
            unit = match.group(2)
            if unit.startswith('дн'):
                return now + timedelta(days=amount)
            if unit.startswith('час'):
                return now + timedelta(hours=amount)
            if unit.startswith('мин'):
                return now + timedelta(minutes=amount)
    else:
        s = s.replace('Z', '+00:00')

    for fmt in (
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%d.%m.%Y %H:%M',
        '%d.%m.%Y',
        '%d.%m %H:%M',
        '%d.%m',
    ):
        try:
            parsed = datetime.strptime(s, fmt)
            if fmt == '%d.%m':
                parsed = parsed.replace(year=now.year)
            if parsed.tzinfo is None:
                return parsed
            return parsed
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


@tasks_bp.route('/new', methods=['GET', 'POST'])
def create_task():
    """Создание новой задачи"""
    if request.method == 'POST':
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Не авторизован'}), 401
        
        title = request.form.get('task-title')
        description = request.form.get('task-description')
        due_date = request.form.get('task-datetime')
        priority = request.form.get('priority', 'medium')
        category = request.form.get('category', 'personal')
        
        if not title:
            return jsonify({'error': 'Название задачи обязательно'}), 400

        due_dt = _parse_due_date(due_date)
        if due_date and str(due_date).strip() and due_dt is None:
            return jsonify({'error': 'Некорректная дата и время'}), 400

        task = Task(
            title=title,
            description=description,
            due_date=due_dt,
            priority=priority,
            category=category,
            user_id=user_id
        )
        
        db.session.add(task)
        db.session.commit()
        
        return jsonify({'success': True, 'task_id': task.id})
    
    return render_template('addtask.html')


@tasks_bp.route('/list', methods=['GET'])
def list_tasks():
    """Получение списка задач пользователя"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Не авторизован'}), 401

    tasks = Task.query.filter_by(user_id=user_id).order_by(Task.created_at.desc()).all()
    now = datetime.utcnow()

    tasks_data = []
    for task in tasks:
        due_date = task.due_date
        due_date_iso = due_date.isoformat() if due_date else None
        is_overdue = task.is_overdue()
        due_in_seconds = None
        urgency = 'normal'
        if due_date:
            due_in_seconds = int((due_date - now).total_seconds())
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

    return jsonify(tasks_data)


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
            'due_date': task.due_date.isoformat() if task.due_date else None,
            'category': task.category
        })
    
    elif request.method == 'PUT':
        data = request.get_json() or request.form

        if 'title' in data:
            task.title = data['title']
        if 'description' in data:
            task.description = data['description']
        if 'priority' in data:
            task.priority = data['priority']
        if 'status' in data:
            task.status = data['status']
            if task.status == 'completed' and task.completed_at is None:
                task.complete()
        if 'due_date' in data:
            due_dt = _parse_due_date(data['due_date'])
            if data.get('due_date') and str(data.get('due_date')).strip() and due_dt is None:
                return jsonify({'error': 'Некорректная дата'}), 400
            task.due_date = due_dt
        if 'category' in data:
            task.category = data['category']

        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(task)
        db.session.commit()
        return jsonify({'success': True})


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
