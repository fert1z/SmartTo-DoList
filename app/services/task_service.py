"""
Task management service
"""
from __future__ import annotations
from datetime import datetime
from app import db
from app.models import Task, User, TaskStatus, TaskPriority
from app.utils import parse_natural_time_local

def get_tasks_for_user(user_id: int) -> list[Task]:
    """Get all tasks for a user."""
    return Task.query.filter_by(user_id=user_id).all()

def create_task(user_id: int, data: dict) -> Task:
    """Create a new task."""
    title = str(data.get('title', '')).strip()
    if not title:
        raise ValueError("Task title is required")
    if len(title) > 200:
        raise ValueError("Task title is too long")

    priority_str = str(data.get('priority', 'medium')).strip().lower()
    priority = TaskPriority(priority_str) if priority_str in [p.value for p in TaskPriority] else TaskPriority.MEDIUM
    
    category = str(data.get('category', 'personal')).strip().lower()
    if category not in ['personal', 'work', 'shopping', 'health', 'other', 'study']:
        category = 'personal'

    user = db.session.get(User, user_id)
    user_timezone = user.timezone if user and user.timezone else 'UTC'

    due_date_exact = data.get('due_date_exact')
    due_date_smart = data.get('due_date_smart')
    due_dt = _parse_due_date(due_date_exact, due_date_smart, user_timezone)
    if (due_date_exact or due_date_smart) and due_dt is None:
        raise ValueError("Could not recognize the date. Try a different format or phrase.")

    task = Task(
        title=title,
        description=str(data.get('description', '')).strip(),
        due_date=due_dt,
        priority=priority,
        category=category,
        user_id=user_id,
    )
    db.session.add(task)
    db.session.commit()
    return task

def get_task_by_id(task_id: int, user_id: int) -> Task | None:
    """Get a task by its ID."""
    return Task.query.filter_by(id=task_id, user_id=user_id).first()

def update_task(task: Task, data: dict) -> Task:
    """Update a task."""
    if 'title' in data:
        new_title = str(data.get('title', '')).strip()
        if not new_title:
            raise ValueError("Task title is required")
        task.title = new_title[:200]

    if 'description' in data:
        task.description = str(data.get('description', ''))

    if 'priority' in data:
        priority_str = str(data.get('priority', '')).strip().lower()
        if priority_str in [p.value for p in TaskPriority]:
            task.priority = TaskPriority(priority_str)

    if 'status' in data:
        status_str = str(data.get('status', '')).strip().lower()
        if status_str in [s.value for s in TaskStatus]:
            task.status = TaskStatus(status_str)

    if 'due_date' in data:
        user = db.session.get(User, task.user_id)
        user_timezone = user.timezone if user and user.timezone else 'UTC'
        task.due_date = _parse_due_date(data.get('due_date'), None, user_timezone)

    if 'category' in data:
        new_category = str(data.get('category', '')).strip().lower()
        if new_category in ['personal', 'work', 'shopping', 'health', 'other', 'study']:
            task.category = new_category
            
    db.session.commit()
    return task

def delete_task(task: Task) -> None:
    """Delete a task."""
    db.session.delete(task)
    db.session.commit()

def complete_task(task: Task) -> Task:
    """Mark a task as complete."""
    task.complete()
    db.session.commit()
    return task

def _parse_due_date(exact_date_str: str, smart_date_str: str, user_timezone: str = 'UTC') -> datetime | None:
    """
    Parses a date. Priority is given to the exact date from the calendar.
    If it is not set, a local "smart" parsing is used.
    Returns a datetime object in UTC.
    """
    if exact_date_str:
        try:
            dt = datetime.fromisoformat(exact_date_str)
            if dt.tzinfo is None:
                try:
                    tz = pytz.timezone(user_timezone)
                except pytz.UnknownTimeZoneError:
                    tz = pytz.utc
                dt = tz.localize(dt).astimezone(pytz.utc)
            return dt
        except ValueError:
            pass

    if smart_date_str:
        return parse_natural_time_local(smart_date_str, user_timezone)

    return None