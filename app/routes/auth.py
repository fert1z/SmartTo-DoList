"""
Authentication routes
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.services.auth_service import auth_service

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page and handler"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            user = auth_service.login_user(username, password)
            
            session.clear()
            session.permanent = True
            session['user_id'] = user.id
            session['username'] = user.username
            logger.info(f"User login successful")
            return redirect(url_for('main.dashboard'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('login.html'), 401
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'error')
            return render_template('login.html'), 500

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page and handler"""
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            auth_service.register_user(username, password, confirm_password)
            
            logger.info(f"New user registered: {username}")
            flash('You have successfully registered! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('registration.html'), 400
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'error')
            return render_template('registration.html'), 500

    return render_template('registration.html')


@auth_bp.route('/logout')
def logout():
    """Logout"""
    logger.info(f"User logged out")
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('main.index'))