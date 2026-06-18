"""
Authentication routes
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.limiter import limiter
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
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            auth_service.register_user(username, email, password, confirm_password)
            
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


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('5 per hour')
def forgot_password():
    """Forgot password"""
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip().lower()
            auth_service.forgot_password(email)
            flash('If this email is registered, a password reset link will be sent.', 'info')
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Forgot password error: {str(e)}")
            flash('An error occurred', 'error')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password with a one-time token."""
    token = request.args.get('token') if request.method == 'GET' else request.form.get('token')
    if request.method == 'POST':
        try:
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            auth_service.reset_password(token, password, confirm_password)
            flash('Your password has been successfully reset. Please log in with your new password.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), 'error')
            return render_template('reset_password.html', token=token), 400

    return render_template('reset_password.html', token=token)