"""
Main application routes
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from app.models import Task
from app import db
from app.utils import require_login
import logging
import telebot
from config import Config

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

bot = telebot.TeleBot(Config.TELEGRAM_BOT_TOKEN, threaded=False)

@main_bp.route(f"/{Config.TELEGRAM_BOT_TOKEN}", methods=['POST'])
def telegram_webhook():
    """Webhook for Telegram bot"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Forbidden', 403

@main_bp.route('/')
def index():
    """Main page"""
    return render_template('main_page.html')


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@main_bp.route('/dashboard')
@require_login
def dashboard():
    """Dashboard"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        logger.error(f"Error loading dashboard: {str(e)}")
        return render_template('error500.html'), 500


@main_bp.route('/addtask')
@require_login
def addtask():
    """Add task page"""
    try:
        return render_template('addtask.html')
    except Exception as e:
        logger.error(f"Error loading addtask page: {str(e)}")
        return render_template('error500.html'), 500