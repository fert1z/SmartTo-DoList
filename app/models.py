"""
Модели данных приложения
"""
from __future__ import annotations

from datetime import datetime, timezone

from app import db
from werkzeug.security import generate_password_hash, check_password_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(256), nullable=False)
    
    is_email_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    email_confirmed_at = db.Column(db.DateTime, nullable=True)

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


class Task(db.Model):
    """Модель задачи"""
    __tablename__ = 'tasks'
    __table_args__ = (
        db.Index('ix_tasks_user_status', 'user_id', 'status'),
        db.Index('ix_tasks_user_duedate', 'user_id', 'due_date'),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    priority = db.Column(db.String(10), default='medium')
    status = db.Column(db.String(20), default='pending')
    due_date = db.Column(db.DateTime)
    category = db.Column(db.String(50), default='personal')
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=_utcnow, onupdate=_utcnow)
    completed_at = db.Column(db.DateTime)
    notified_at = db.Column(db.DateTime)
    version = db.Column(db.Integer, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self) -> str:
        return f'<Task {self.title}>'

    def complete(self) -> None:
        self.status = 'completed'
        self.completed_at = _utcnow()

    def is_overdue(self) -> bool:
        if not self.due_date or self.status == 'completed':
            return False
        due_dt = self.due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        return _utcnow() > due_dt


class EmailConfirmationToken(db.Model):
    """Одноразовый токен для подтверждения email при регистрации."""
    __tablename__ = 'email_confirmation_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref=db.backref('email_confirmation_tokens', lazy=True))


class TelegramLinkCode(db.Model):
    """Одноразовый код привязки Telegram к аккаунту."""
    __tablename__ = 'telegram_link_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    user = db.relationship('User', backref=db.backref('telegram_link_codes', lazy=True))


class PasswordResetToken(db.Model):
    """Одноразовый токен для сброса пароля."""
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy=True))


class EmailChangeRequest(db.Model):
    """Запрос на подтверждение изменения email."""
    __tablename__ = 'email_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    new_email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    user = db.relationship('User', backref=db.backref('email_change_requests', lazy=True))


class ReminderLog(db.Model):
    """Лог отправок напоминаний для задач."""
    __tablename__ = 'reminder_logs'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    reminded_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    reminder_type = db.Column(db.String(50), nullable=False, default='due_soon')
    payload = db.Column(db.Text)

    def __repr__(self) -> str:
        return f'<ReminderLog task_id={self.task_id} type={self.reminder_type}>'