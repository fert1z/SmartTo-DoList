"""
Модели данных приложения
"""
from app import db
from datetime import datetime


class User(db.Model):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    tasks = db.relationship('Task', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        """Устанавливает пароль (нужно добавить werkzeug.security)"""
        # from werkzeug.security import generate_password_hash
        # self.password = generate_password_hash(password)
        self.password = password  # TODO: Реализовать хеширование
    
    def check_password(self, password):
        """Проверяет пароль"""
        # from werkzeug.security import check_password_hash
        # return check_password_hash(self.password, password)
        return self.password == password  # TODO: Реализовать проверку хеша


class Task(db.Model):
    """Модель задачи"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    description = db.Column(db.Text)
    priority = db.Column(db.String(10), default='medium')  # low, medium, high
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed
    due_date = db.Column(db.DateTime)
    category = db.Column(db.String(50), default='personal')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Внешний ключ
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<Task {self.title}>'
    
    def complete(self):
        """Отмечает задачу как выполненную"""
        self.status = 'completed'
        self.completed_at = datetime.utcnow()
    
    def is_overdue(self):
        """Проверяет, просрочена ли задача"""
        if self.due_date and self.status != 'completed':
            return datetime.utcnow() > self.due_date
        return False
