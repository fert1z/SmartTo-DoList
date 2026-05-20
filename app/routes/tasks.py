"""
Маршруты для работы с задачами
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, session
from app.models import Task, User
from app import db
from app.utils import require_login
import logging

logger = logging.getLogger(__name__)
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
@require_login
def create_task():
    """Создание новой задачи"""
    if request.method == 'POST':
        try:
            user_id = session.get('user_id')
            title = request.form.get('task-title', '').strip()
            description = request.form.get('task-description', '').strip()
            due_date = request.form.get('task-datetime')
            priority = request.form.get('priority', 'medium')
            category = request.form.get('category', 'personal')

            if not title:
                return jsonify({'error': 'Название задачи обязательно'}), 400

            if len(title) > 200:
                return jsonify({'error': 'Название задачи слишком длинное'}), 400

            if priority not in ['low', 'medium', 'high']:
                priority = 'medium'

            if category not in ['personal', 'work', 'shopping', 'health', 'other']:
                category = 'personal'

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

            logger.info(f"Task created by user {user_id}: {title}")
            return jsonify({'success': True, 'task_id': task.id})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating task: {str(e)}")
            return jsonify({'error': 'Ошибка при создании задачи'}), 500

    return render_template('addtask.html')


@tasks_bp.route('/list', methods=['GET'])
@require_login
def list_tasks():
    """Получение списка задач пользователя"""
    try:
        user_id = session.get('user_id')
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

    except Exception as e:
        logger.error(f"Error listing tasks: {str(e)}")
        return jsonify({'error': 'Ошибка при получении задач'}), 500


@tasks_bp.route('/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@require_login
def task_detail(task_id):
    """Получение, обновление или удаление задачи"""
    try:
        user_id = session.get('user_id')
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

            if 'title' in data and data['title']:
                task.title = str(data['title']).strip()[:200]
            if 'description' in data:
                task.description = data['description']
            if 'priority' in data and data['priority'] in ['low', 'medium', 'high']:
                task.priority = data['priority']
            if 'status' in data and data['status'] in ['pending', 'in_progress', 'completed']:
                task.status = data['status']
            if 'due_date' in data:
                task.due_date = _parse_due_date(data['due_date'])
            if 'category' in data and data['category'] in ['personal', 'work', 'shopping', 'health', 'other']:
                task.category = data['category']

            db.session.commit()
            logger.info(f"Task {task_id} updated by user {user_id}")
            return jsonify({'success': True})

        elif request.method == 'DELETE':
            db.session.delete(task)
            db.session.commit()
            logger.info(f"Task {task_id} deleted by user {user_id}")
            return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in task_detail: {str(e)}")
        return jsonify({'error': 'Ошибка при работе с задачей'}), 500


@tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@require_login
def complete_task(task_id):
    """Отметить задачу как выполненную"""
    try:
        user_id = session.get('user_id')
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()

        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404

        task.complete()
        db.session.commit()

        logger.info(f"Task {task_id} marked as complete by user {user_id}")
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error completing task: {str(e)}")
        return jsonify({'error': 'Ошибка при выполнении операции'}), 500
