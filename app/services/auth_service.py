"""
Authentication service
"""
import secrets
from datetime import datetime, timedelta, timezone
from flask import url_for
from app import db
from app.models import User, PasswordResetToken
from app.utils import validate_email_format, validate_username, validate_password
from app.mail_utils import send_email

class AuthService:
    def login_user(self, username, password):
        if not username or not password:
            raise ValueError('Please fill in all fields')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            return user
        raise ValueError('Invalid credentials')

    def register_user(self, username, email, password, confirm_password):
        if not all([username, email, password, confirm_password]):
            raise ValueError('Please fill in all fields')

        validate_username(username)
        validate_email_format(email)
        validate_password(password)

        if password != confirm_password:
            raise ValueError('Passwords do not match')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            raise ValueError('A user with this username or email already exists')

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def forgot_password(self, email):
        validate_email_format(email)

        user = User.query.filter_by(email=email).first()
        if user:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            
            PasswordResetToken.query.filter_by(user_id=user.id).delete()
            reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
            db.session.add(reset_token)
            db.session.commit()

            reset_url = url_for('auth.reset_password', token=token, _external=True)
            subject = 'SmartTo-DoList: Password Reset'
            body_text = f"To reset your password, please visit the following link: {reset_url}"
            send_email(to_email=email, subject=subject, body_text=body_text)

    def reset_password(self, token, password, confirm_password):
        if not token:
            raise ValueError('Invalid or missing password reset link')

        reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
        if not reset_token or reset_token.expires_at < datetime.now(timezone.utc):
            raise ValueError('The password reset link is invalid or has expired')

        if password != confirm_password:
            raise ValueError('Passwords do not match')

        validate_password(password)

        user = db.session.get(User, reset_token.user_id)
        if not user:
            raise ValueError('User not found')

        user.set_password(password)
        reset_token.used = True
        db.session.commit()

auth_service = AuthService()