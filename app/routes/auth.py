"""
Маршруты аутентификации
"""
from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import User
from app import db

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа и обработка входа"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('login.html', error='Заполните все поля')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.dashboard'))
        else:
            return render_template('login.html', error='Неверные учетные данные')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Страница регистрации и обработка регистрации"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Валидация
        if not all([username, email, password, confirm_password]):
            return render_template('registration.html', error='Заполните все поля')
        
        if password != confirm_password:
            return render_template('registration.html', error='Пароли не совпадают')
        
        if len(password) < 8:
            return render_template('registration.html', error='Пароль должен быть не менее 8 символов')
        
        if User.query.filter_by(username=username).first():
            return render_template('registration.html', error='Пользователь уже существует')
        
        if User.query.filter_by(email=email).first():
            return render_template('registration.html', error='Email уже зарегистрирован')
        
        # Создаем нового пользователя
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        
        return redirect(url_for('main.dashboard'))
    
    return render_template('registration.html')


@auth_bp.route('/logout')
def logout():
    """Выход из системы"""
    session.clear()
    return redirect(url_for('main.index'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Восстановление пароля"""
    if request.method == 'POST':
        email = request.form.get('email')
        # TODO: Реализовать отправку письма для восстановления пароля
        return render_template('forgot_password.html', success='Письмо отправлено')
    
    return render_template('forgot_password.html')
