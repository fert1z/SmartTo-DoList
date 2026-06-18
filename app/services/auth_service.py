"""
Authentication service
"""
from app import db
from app.models import User
from app.utils import validate_username, validate_password

class AuthService:
    def login_user(self, username, password):
        if not username or not password:
            raise ValueError('Please fill in all fields')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            return user
        raise ValueError('Invalid credentials')

    def register_user(self, username, password, confirm_password):
        if not all([username, password, confirm_password]):
            raise ValueError('Please fill in all fields')

        validate_username(username)
        validate_password(password)

        if password != confirm_password:
            raise ValueError('Passwords do not match')

        if User.query.filter_by(username=username).first():
            raise ValueError('A user with this username already exists')

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

auth_service = AuthService()