"""
Модели данных приложения
"""
from app import db
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    timezone = db.Column(db.String(32), nullable=False, default='UTC')
    telegram_user_id = db.Column(db.BigInteger, unique=True, nullable=True, index=True)
    
    # Связи
    tasks = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Устанавливает пароль с хешированием."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Проверяет пароль по хешу."""
        return check_password_hash(self.password, password)


class Task(db.Model):
    """Модель задачи"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    priority = db.Column(db.String(10), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    due_date = db.Column(db.DateTime(timezone=True))
    category = db.Column(db.String(50), default='personal')
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime(timezone=True))
    notified_at = db.Column(db.DateTime(timezone=True))
    
    # Внешний ключ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<Task {self.title}>'
    
    def complete(self):
        """Отмечает задачу как выполненную"""
        self.status = 'completed'
        self.completed_at = datetime.now(timezone.utc)
    
    def is_overdue(self):
        """Проверяет, просрочена ли задача"""
        if self.due_date and self.status != 'completed':
            due = self.due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) > due
        return False


class PasswordResetToken(db.Model):
    """Токен для сброса пароля."""
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)

    user = db.relationship('User', backref=db.backref('reset_tokens', lazy=True))


class TelegramLinkCode(db.Model):
    """Одноразовый код привязки Telegram к аккаунту (выдаётся в веб-настройках)."""
    __tablename__ = 'telegram_link_codes'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)

    user = db.relationship('User', backref=db.backref('telegram_link_codes', lazy=True))
