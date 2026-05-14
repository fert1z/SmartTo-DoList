from datetime import datetime, timedelta, timezone
import os
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from app.models import Task, User
from app import db
from telebot import types
from tg_bot.main_bot import get_bot
from app.utils import format_datetime_for_user

logger = logging.getLogger(__name__)
_scheduler = None


def _should_notify(task: Task, now: datetime) -> bool:
    if task.status == 'completed' or not task.due_date:
        return False
    due = task.due_date
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    if due <= now:
        return False
    if task.notified_at and task.notified_at.tzinfo is None:
        task_notified = task.notified_at.replace(tzinfo=timezone.utc)
    else:
        task_notified = task.notified_at
    if task_notified and task_notified >= now - timedelta(minutes=30):
        return False
    return now + timedelta(minutes=15) >= due


def send_task_reminders(app):
    with app.app_context():
        now = datetime.now(timezone.utc)
        upcoming = (
            Task.query.filter(Task.status != 'completed')
            .filter(Task.due_date != None)
            .order_by(Task.due_date.asc())
            .limit(100)
            .all()
        )

        bot = None
        for task in upcoming:
            if not _should_notify(task, now):
                continue
            user = User.query.get(task.user_id)
            if not user or not user.telegram_user_id:
                continue
            if bot is None:
                try:
                    bot = get_bot()
                except Exception as error:
                    logger.exception('Telegram bot not available for reminders: %s', error)
                    return
            due_str = format_datetime_for_user(task.due_date, user.timezone or 'UTC')
            delta = task.due_date - now
            minutes_left = int(delta.total_seconds() // 60)
            
            # Добавляем кнопки управления
            kb = types.InlineKeyboardMarkup()
            kb.add(types.InlineKeyboardButton("✅ Выполнено", callback_data=f"d:{task.id}"))
            kb.add(types.InlineKeyboardButton("⏰ Отложить на 1 час", callback_data=f"snooze:{task.id}:60"))

            text = (
                f'⏰ Напоминание: задача <b>#{task.id}</b> «{task.title}»'
                f' должна быть завершена к {due_str} ({minutes_left} мин).'
            )
            try:
                bot.send_message(user.telegram_user_id, text, reply_markup=kb)
                task.notified_at = now
                db.session.commit()
            except Exception as error:
                logger.exception('Не удалось отправить уведомление для задачи %s: %s', task.id, error)


def init_scheduler(app):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    if not app.config.get('SCHEDULER_ENABLED', True):
        return None

    _scheduler = BackgroundScheduler(timezone=timezone.utc)
    interval_minutes = app.config.get('REMINDER_INTERVAL_MINUTES', 5)
    _scheduler.add_job(
        send_task_reminders,
        'interval',
        args=[app],
        minutes=interval_minutes,
        next_run_time=datetime.now(timezone.utc),
    )
    _scheduler.start()
    logger.info('Scheduler started: reminders every %s minutes', interval_minutes)
    return _scheduler


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
