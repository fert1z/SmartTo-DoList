"""Tests for the SmartTo-DoList application"""
import pytest
from flask import session
from app import create_app, db
from app.models import User, Task, TaskStatus
from datetime import datetime, timedelta, timezone
from app.utils import validate_username, validate_password, parse_natural_time_local

@pytest.fixture
def app():
    """Creates a test application"""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Creates a test client"""
    return app.test_client()

@pytest.fixture
def auth_user(app):
    """Creates a test user"""
    user = User(username='testuser')
    user.set_password('testpass123')
    db.session.add(user)
    db.session.commit()
    return user

@pytest.fixture
def another_user(app):
    """Creates a second test user"""
    user = User(username='anotheruser')
    user.set_password('anotherpass')
    db.session.add(user)
    db.session.commit()
    return user

class TestAuth:
    """Authentication tests"""

    def test_register_valid(self, client):
        """Test successful registration"""
        response = client.post('/auth/register', data={
            'username': 'newuser',
            'password': 'Password123!',
            'confirm_password': 'Password123!'
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'You have successfully registered!' in response.data

    def test_register_invalid(self, client):
        """Test registration with invalid data"""
        response = client.post('/auth/register', data={'username': 'new'}, follow_redirects=True)
        assert response.status_code == 400
        assert b'Please fill in all fields' in response.data

    def test_login_valid(self, client, auth_user):
        """Test successful login"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=True)
        assert response.status_code == 200
        with client.session_transaction() as sess:
            assert sess.get('user_id') == auth_user.id

    def test_login_invalid(self, client, auth_user):
        """Test login with invalid password"""
        response = client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
        assert b'Invalid credentials' in response.data

    def test_logout(self, client, auth_user):
        """Test logout"""
        client.post('/auth/login', data={'username': 'testuser', 'password': 'testpass123'})
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200
        assert b'You have been logged out.' in response.data
        with client.session_transaction() as sess:
            assert 'user_id' not in sess

class TestTasks:
    """Task management tests"""

    @pytest.fixture(autouse=True)
    def login(self, client, auth_user):
        """Automatic login for all tests in this class"""
        with client.session_transaction() as sess:
            sess['user_id'] = auth_user.id
        yield

    def test_create_task(self, client):
        """Test creating a task"""
        response = client.post('/api/tasks', json={'title': 'Test Task'})
        assert response.status_code == 200
        task = db.session.get(Task, response.get_json()['task_id'])
        assert task.title == 'Test Task'

    def test_list_tasks(self, client, auth_user):
        """Test listing tasks"""
        db.session.add(Task(title='Task 1', user_id=auth_user.id))
        db.session.commit()
        response = client.get('/api/tasks')
        assert response.status_code == 200
        assert len(response.get_json()) == 1

    def test_complete_task(self, client, auth_user):
        """Test completing a task"""
        task = Task(title='Test Task', user_id=auth_user.id)
        db.session.add(task)
        db.session.commit()
        client.post(f'/api/tasks/{task.id}/complete')
        completed_task = db.session.get(Task, task.id)
        assert completed_task.status == TaskStatus.COMPLETED

class TestModels:
    """Model tests"""

    def test_password_hashing(self):
        """Test password hashing"""
        user = User(username='testuser')
        password = 'testpass123'
        user.set_password(password)
        assert user.password != password
        assert user.check_password(password)
        assert not user.check_password('wrongpassword')

    def test_user_avatar(self):
        """Test avatar URL generation"""
        user = User(username='testuser')
        avatar_url = user.avatar(128)
        assert 'gravatar.com' in avatar_url
        assert 's=128' in avatar_url
        assert 'identicon' in avatar_url

class TestUtils:
    """Validation utility tests"""

    def test_validate_username(self):
        """Test username validation"""
        with pytest.raises(ValueError, match='at least 3 characters'):
            validate_username('ab')
        with pytest.raises(ValueError, match='can only contain letters, numbers, and underscores'):
            validate_username('user@name')
        validate_username('validuser')

    def test_validate_password(self):
        """Test password validation"""
        with pytest.raises(ValueError, match='at least 8 characters'):
            validate_password('short')
        with pytest.raises(ValueError, match='is required'):
            validate_password('')
        validate_password('Validpass123!')

class TestNaturalTimeParser:
    """Tests for the natural language time parser"""

    @pytest.mark.parametrize("text, expected_delta_days", [
        ("завтра", 1),
        ("послезавтра", 2),
        ("через день", 2),
        ("вчера", -1),
        ("позавчера", -2),
    ])
    def test_abstract_days(self, text, expected_delta_days):
        now = datetime.now(timezone.utc)
        result = parse_natural_time_local(text)
        assert result.day == (now + timedelta(days=expected_delta_days)).day

    def test_relative_time(self):
        now = datetime.now(timezone.utc)
        result = parse_natural_time_local("через 2 часа 30 минут")
        assert result is not None
        assert result > now + timedelta(hours=2, minutes=29)
        assert result < now + timedelta(hours=2, minutes=31)

    @pytest.mark.parametrize("text, weekday", [
        ("в понедельник", 0),
        ("во вторник", 1),
        ("в среду", 2),
        ("в четверг", 3),
        ("в пятницу", 4),
        ("в субботу", 5),
        ("в воскресенье", 6),
    ])
    def test_weekdays(self, text, weekday):
        result = parse_natural_time_local(text)
        assert result.weekday() == weekday

    def test_fuzzy_time(self):
        result = parse_natural_time_local("вечером")
        assert result.hour == 18

    def test_exact_time(self):
        result = parse_natural_time_local("в 14:30")
        assert result.hour == 14
        assert result.minute == 30

    def test_no_time(self):
        assert parse_natural_time_local("просто текст") is None