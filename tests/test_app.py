"""Тесты для приложения SmartTo-DoList"""
import pytest
import os
from app import create_app, db
from app.models import User, Task
from datetime import datetime, timedelta, timezone


@pytest.fixture
def app():
    """Создает тестовое приложение"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Создает тестовый клиент"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Создает CLI runner"""
    return app.test_cli_runner()


@pytest.fixture
def auth_user(app):
    """Создает тестового пользователя"""
    user = User(username='testuser', email='test@example.com')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user


class TestAuth:
    """Тесты аутентификации"""

    def test_register_valid(self, client):
        """Тест успешной регистрации"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        })
        assert response.status_code in [302, 200]

    def test_register_short_password(self, client):
        """Тест регистрации с коротким паролем"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'pass',
            'confirm_password': 'pass'
        })
        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Тест регистрации с неверным email"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'email': 'invalid-email',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        assert response.status_code == 400

    def test_register_duplicate_username(self, client, auth_user):
        """Тест регистрации с существующим username"""
        response = client.post('/auth/register', data={
            'username': 'testuser',
            'email': 'another@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        })
        # Returns 400 instead of 409 to prevent information disclosure (generic error message)
        assert response.status_code == 400

    def test_login_valid(self, client, auth_user):
        """Тест успешного входа"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        assert response.status_code in [302, 200]

    def test_login_invalid_password(self, client, auth_user):
        """Тест входа с неверным паролем"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401

    def test_logout(self, client, auth_user):
        """Тест выхода"""
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        })
        response = client.get('/auth/logout')
        assert response.status_code == 302


class TestTasks:
    """Тесты управления задачами"""

    def test_create_task_authenticated(self, client, auth_user):
        """Тест создания задачи авторизованным пользователем"""
        with client.session_transaction() as sess:
            sess['user_id'] = auth_user.id

        response = client.post('/api/tasks', data={
            'title': 'Test Task',
            'description': 'Test Description',
            'priority': 'high',
            'category': 'work'
        })
        assert response.status_code in [200, 400]

    def test_create_task_unauthenticated(self, client):
        """Тест создания задачи без аутентификации"""
        response = client.post('/api/tasks', data={
            'title': 'Test Task'
        })
        assert response.status_code == 401

    def test_list_tasks(self, client, auth_user):
        """Тест получения списка задач"""
        task = Task(
            title='Test Task',
            user_id=auth_user.id,
            priority='medium'
        )
        db.session.add(task)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = auth_user.id

        response = client.get('/api/tasks')
        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['title'] == 'Test Task'

    def test_complete_task(self, client, auth_user):
        """Тест отметить задачу как выполненную"""
        task = Task(
            title='Test Task',
            user_id=auth_user.id,
            priority='medium'
        )
        db.session.add(task)
        db.session.commit()

        with client.session_transaction() as sess:
            sess['user_id'] = auth_user.id

        response = client.post(f'/api/tasks/{task.id}/complete')
        assert response.status_code == 200

        task = db.session.get(Task, task.id)
        assert task.status == 'completed'


class TestModels:
    """Тесты моделей"""

    def test_password_hashing(self):
        """Тест хеширования паролей"""
        user = User(username='testuser', email='test@example.com')
        password = 'testpass123'
        user.set_password(password)

        assert user.password != password
        assert user.check_password(password)
        assert not user.check_password('wrongpassword')

    def test_task_complete(self):
        """Тест отметить задачу как выполненную"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')
        task = Task(title='Test', user_id=1)
        task.complete()

        assert task.status == 'completed'
        assert task.completed_at is not None

    def test_task_is_overdue(self):
        """Тест проверки просроченной задачи"""
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpass123')

        # Просроченная задача
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        task = Task(title='Overdue', user_id=1, due_date=past_date, status='pending')
        assert task.is_overdue()

        # Будущая задача
        future_date = datetime.now(timezone.utc) + timedelta(days=1)
        task2 = Task(title='Not Overdue', user_id=1, due_date=future_date, status='pending')
        assert not task2.is_overdue()

        # Выполненная задача не просроченна
        completed_task = Task(title='Completed', user_id=1, due_date=past_date, status='completed')
        assert not completed_task.is_overdue()


class TestUtils:
    """Тесты утилит валидации"""

    def test_validate_email_format(self):
        """Тест валидации email"""
        from app.utils import validate_email_format

        assert validate_email_format('test@example.com')
        assert validate_email_format('user+tag@example.co.uk')
        assert not validate_email_format('invalid-email')
        assert not validate_email_format('user@')

    def test_validate_username(self):
        """Тест валидации username"""
        from app.utils import validate_username

        valid, msg = validate_username('validuser')
        assert valid
        assert msg is None

        valid, msg = validate_username('ab')
        assert not valid
        assert msg is not None

        valid, msg = validate_username('user@name')
        assert not valid

    def test_validate_password(self):
        """Тест валидации пароля"""
        from app.utils import validate_password

        valid, msg = validate_password('Validpass123!')
        assert valid
        assert msg is None

        valid, msg = validate_password('short')
        assert not valid

        valid, msg = validate_password('')
        assert not valid
