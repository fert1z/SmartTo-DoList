"""
Application data models
"""
from __future__ import annotations
import hashlib
from datetime import datetime, timezone
import enum

from app import db
from werkzeug.security import generate_password_hash, check_password_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, enum.Enum):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    COMPLETED = 'COMPLETED'


class TaskPriority(str, enum.Enum):
    LOW = 'LOW'
    MEDIUM = 'MEDIUM'
    HIGH = 'HIGH'


class User(db.Model):
    """User model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(256), nullable=False)
    
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)

    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    timezone = db.Column(db.String(50), default='UTC')

    tasks = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<User {self.username}>'

    def set_password(self, password: str) -> None:
        self.password = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password, password)

    def avatar(self, size: int) -> str:
        """Generates a user avatar URL using Gravatar."""
        digest = hashlib.md5(self.username.lower().encode('utf-8')).hexdigest()
        return f'https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}'


class Task(db.Model):
    """Task model"""
    __tablename__ = 'tasks'
    __table_args__ = (
        db.Index('ix_tasks_user_status', 'user_id', 'status'),
        db.Index('ix_tasks_user_duedate', 'user_id', 'due_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    priority = db.Column(db.Enum(TaskPriority, name='taskpriority', create_type=False), default=TaskPriority.MEDIUM, nullable=False)
    status = db.Column(db.Enum(TaskStatus, name='taskstatus', create_type=False), default=TaskStatus.PENDING, nullable=False)
    due_date = db.Column(db.DateTime)
    category = db.Column(db.String(50), default='personal')
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    completed_at = db.Column(db.DateTime)
    notified_at = db.Column(db.DateTime)
    version = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Каскадное удаление логов при удалении задачи
    reminder_logs = db.relationship('ReminderLog', backref='task', lazy=True, cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Task {self.title}>'

    def complete(self) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = _utcnow()

    def is_overdue(self) -> bool:
        if not self.due_date or self.status == TaskStatus.COMPLETED:
            return False
        due_dt = self.due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        return _utcnow() > due_dt


class TelegramLinkCode(db.Model):
    """One-time code for linking a Telegram account."""
    __tablename__ = 'telegram_link_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('telegram_link_codes', lazy=True))


class ReminderLog(db.Model):
    """Log of reminder notifications for tasks."""
    __tablename__ = 'reminder_logs'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reminded_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    reminder_type = db.Column(db.String(50), nullable=False, default='due_soon')
    payload = db.Column(db.Text)

    def __repr__(self) -> str:
        return f'<ReminderLog task_id={self.task_id} type={self.reminder_type}>'