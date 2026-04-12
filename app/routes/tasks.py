"""
Маршруты для работы с задачами
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, session
from app.models import Task, User
from app import db

tasks_bp = Blueprint('tasks', __name__)


def _parse_due_date(raw):
    """Парсинг значения datetime-local или ISO; пустое — None."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().replace('Z', '+00:00')
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
    
    tasks = Task.query.filter_by(user_id=user_id).all()
    
    tasks_data = [{
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'status': task.status,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'category': task.category
    } for task in tasks]
    
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
        if 'due_date' in data:
            task.due_date = data['due_date']
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
