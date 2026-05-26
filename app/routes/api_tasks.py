"""
REST API маршруты для работы с задачами.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request, session

from app import db
from app.models import Task, User
from app.utils import require_login
from app.openai_reminders import parse_natural_time_with_openai

logger = logging.getLogger(__name__)

api_tasks_bp = Blueprint('api_tasks', __name__, url_prefix='/api/tasks')


def _parse_due_date(exact_date_str: str, smart_date_str: str, user_timezone: str = 'UTC') -> datetime | None:
    """
    Парсит дату. Приоритет у точной даты из календаря.
    Если она не задана, используется "умный" парсинг через OpenAI.
    Возвращает datetime объект в UTC.
    """
    # Приоритет у точной даты
    if exact_date_str:
        try:
            dt = datetime.fromisoformat(exact_date_str)
            # Если от браузера пришло "наивное" время, считаем его локальным и конвертируем в UTC
            # (Это упрощение, в идеале нужно знать timezone браузера)
            if dt.tzinfo is None:
                dt = dt.astimezone(timezone.utc)
            return dt
        except ValueError:
            pass  # Если формат неверный, перейдем к умному парсингу

    # Если точная дата не задана, пробуем "умный" парсинг
    if smart_date_str:
        logger.info(f"Trying to parse natural time: '{smart_date_str}' with timezone {user_timezone}")
        return parse_natural_time_with_openai(smart_date_str, user_timezone)

    return None


def _task_to_json(task: Task) -> dict:
    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'priority': task.priority,
        'status': task.status,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'category': task.category,
    }


@api_tasks_bp.route('', methods=['GET'])
@require_login
def list_tasks_api():
    """Получение списка задач текущего пользователя."""
    try:
        user_id = session.get('user_id')
        tasks = Task.query.filter_by(user_id=user_id).all()
        return jsonify([_task_to_json(t) for t in tasks])
    except Exception as e:
        logger.error('Error listing tasks via API: %s', str(e))
        return jsonify({'error': 'Ошибка при получении задач'}), 500


@api_tasks_bp.route('', methods=['POST'])
@require_login
def create_task_api():
    """Создание новой задачи (JSON)."""
    try:
        user_id = session.get('user_id')
        data = request.get_json(silent=True) or request.form

        title = str(data.get('title', '')).strip()
        description = str(data.get('description', '')).strip()
        priority = str(data.get('priority', 'medium')).strip().lower()
        category = str(data.get('category', 'personal')).strip().lower()
        
        due_date_exact = data.get('due_date_exact')
        due_date_smart = data.get('due_date_smart')

        if not title:
            return jsonify({'error': 'Название задачи обязательно'}), 400
        if len(title) > 200:
            return jsonify({'error': 'Название задачи слишком длинное'}), 400

        if priority not in ['low', 'medium', 'high']:
            priority = 'medium'
        if category not in ['personal', 'work', 'shopping', 'health', 'other', 'study']:
            category = 'personal'

        user = User.query.get(user_id)
        user_timezone = user.timezone if user and user.timezone else 'UTC'

        due_dt = _parse_due_date(due_date_exact, due_date_smart, user_timezone)
        if (due_date_exact or due_date_smart) and due_dt is None:
            return jsonify({'error': 'Не удалось распознать дату. Попробуйте другой формат или фразу.'}), 400

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

        logger.info('Task created via API by user %s', user_id)
        return jsonify({'success': True, 'task_id': task.id})
    except Exception as e:
        db.session.rollback()
        logger.error('Error creating task via API: %s', str(e))
        return jsonify({'error': 'Ошибка при создании задачи'}), 500


@api_tasks_bp.route('/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@require_login
def task_detail_api(task_id: int):
    """Получение/обновление/удаление задачи."""
    try:
        user_id = session.get('user_id')
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404

        if request.method == 'GET':
            return jsonify(_task_to_json(task))

        if request.method == 'DELETE':
            db.session.delete(task)
            db.session.commit()
            logger.info('Task %s deleted via API by user %s', task_id, user_id)
            return jsonify({'success': True})

        # PUT
        data = request.get_json(silent=True) or request.form

        if 'title' in data:
            new_title = str(data.get('title', '')).strip()
            if not new_title:
                return jsonify({'error': 'Название задачи обязательно'}), 400
            task.title = new_title[:200]

        if 'description' in data:
            task.description = str(data.get('description', ''))

        if 'priority' in data:
            new_priority = str(data.get('priority', '')).strip().lower()
            if new_priority in ['low', 'medium', 'high']:
                task.priority = new_priority

        if 'status' in data:
            new_status = str(data.get('status', '')).strip().lower()
            if new_status in ['pending', 'in_progress', 'completed']:
                task.status = new_status

        if 'due_date' in data:
            user = User.query.get(user_id)
            user_timezone = user.timezone if user and user.timezone else 'UTC'
            # Для PUT запросов пока оставляем упрощенную логику, т.к. нет двух полей
            task.due_date = _parse_due_date(data.get('due_date'), None, user_timezone)

        if 'category' in data:
            new_category = str(data.get('category', '')).strip().lower()
            if new_category in ['personal', 'work', 'shopping', 'health', 'other', 'study']:
                task.category = new_category

        db.session.commit()
        logger.info('Task %s updated via API by user %s', task_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error('Error in task_detail_api: %s', str(e))
        return jsonify({'error': 'Ошибка при работе с задачей'}), 500


@api_tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@require_login
def complete_task_api(task_id: int):
    """Отметить задачу как выполненную."""
    try:
        user_id = session.get('user_id')
        task = Task.query.filter_by(id=task_id, user_id=user_id).first()
        if not task:
            return jsonify({'error': 'Задача не найдена'}), 404

        task.complete()
        db.session.commit()
        logger.info('Task %s marked as complete via API by user %s', task_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logger.error('Error completing task via API: %s', str(e))
        return jsonify({'error': 'Ошибка при выполнении операции'}), 500