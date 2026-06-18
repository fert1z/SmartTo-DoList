"""
REST API routes for handling tasks.
"""
from __future__ import annotations

import logging
from datetime import timezone
import enum

from flask import Blueprint, jsonify, request, session
import pytz

from app.models import Task, User
from app.utils import require_login
from app.services import task_service

logger = logging.getLogger(__name__)

api_tasks_bp = Blueprint('api_tasks', __name__, url_prefix='/api/tasks')

def _task_to_json(task: Task, user_timezone: str = 'UTC') -> dict:
    due_date_iso = None
    if task.due_date:
        dt_utc = task.due_date.replace(tzinfo=timezone.utc)
        try:
            tz = pytz.timezone(user_timezone)
            dt_local = dt_utc.astimezone(tz)
            due_date_iso = dt_local.isoformat()
        except pytz.UnknownTimeZoneError:
            due_date_iso = dt_utc.isoformat()

    return {
        'id': task.id,
        'title': task.title,
        'description': task.description,
        'priority': task.priority.value if isinstance(task.priority, enum.Enum) else task.priority,
        'status': task.status.value if isinstance(task.status, enum.Enum) else task.status,
        'due_date': due_date_iso,
        'category': task.category,
    }


@api_tasks_bp.route('', methods=['GET'])
@require_login
def list_tasks_api():
    """Get the list of tasks for the current user."""
    try:
        user_id = session.get('user_id')
        user = task_service.db.session.get(User, user_id)
        user_timezone = user.timezone if user and user.timezone else 'UTC'
        
        tasks = task_service.get_tasks_for_user(user_id)
        return jsonify([_task_to_json(t, user_timezone) for t in tasks])
    except Exception as e:
        logger.error('Error listing tasks via API: %s', str(e))
        return jsonify({'error': 'Error getting tasks'}), 500


@api_tasks_bp.route('', methods=['POST'])
@require_login
def create_task_api():
    """Create a new task (JSON)."""
    try:
        user_id = session.get('user_id')
        data = request.get_json(silent=True) or request.form
        task = task_service.create_task(user_id, data)
        logger.info('Task created via API by user %s', user_id)
        return jsonify({'success': True, 'task_id': task.id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error('Error creating task via API: %s', str(e))
        return jsonify({'error': 'Error creating task'}), 500


@api_tasks_bp.route('/<int:task_id>', methods=['GET', 'PUT', 'DELETE'])
@require_login
def task_detail_api(task_id: int):
    """Get/update/delete a task."""
    try:
        user_id = session.get('user_id')
        task = task_service.get_task_by_id(task_id, user_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if request.method == 'GET':
            user = task_service.db.session.get(User, user_id)
            user_timezone = user.timezone if user and user.timezone else 'UTC'
            return jsonify(_task_to_json(task, user_timezone))

        if request.method == 'DELETE':
            task_service.delete_task(task)
            logger.info('Task %s deleted via API by user %s', task_id, user_id)
            return jsonify({'success': True})

        # PUT
        data = request.get_json(silent=True) or request.form
        task = task_service.update_task(task, data)
        logger.info('Task %s updated via API by user %s', task_id, user_id)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error('Error in task_detail_api: %s', str(e))
        return jsonify({'error': 'Error handling task'}), 500


@api_tasks_bp.route('/<int:task_id>/complete', methods=['POST'])
@require_login
def complete_task_api(task_id: int):
    """Mark a task as completed."""
    try:
        user_id = session.get('user_id')
        task = task_service.get_task_by_id(task_id, user_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        task_service.complete_task(task)
        logger.info('Task %s marked as complete via API by user %s', task_id, user_id)
        return jsonify({'success': True})
    except Exception as e:
        logger.error('Error completing task via API: %s', str(e))
        return jsonify({'error': 'Error during operation'}), 500