"""
Обработчики Telegram-бота: привязка аккаунта, список задач, добавление, выполнение, удаление.
Требуется переменная окружения TELEGRAM_BOT_TOKEN.
"""
from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime, timedelta, timezone

import telebot
from telebot import types

from app import create_app, db
from app.models import Task, TelegramLinkCode, User

logger = logging.getLogger(__name__)

_app = None
bot: telebot.TeleBot | None = None
_handlers_registered = False
_link_attempts: dict[int, list[datetime]] = {}
MAX_LINK_ATTEMPTS = 5
LINK_ATTEMPT_WINDOW_MINUTES = 15

# Ожидание текста новой задачи после команды /add без аргументов
_pending_add_title: dict[int, bool] = {}

PAGE_SIZE = 5


def _clear_pending(uid: int):
    _pending_add_title.pop(uid, None)


def _cleanup_link_attempts() -> None:
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=LINK_ATTEMPT_WINDOW_MINUTES)
    for uid, timestamps in list(_link_attempts.items()):
        filtered = [ts for ts in timestamps if ts >= cutoff]
        if filtered:
            _link_attempts[uid] = filtered
        else:
            _link_attempts.pop(uid, None)


def _register_link_attempt(uid: int) -> int:
    now = datetime.utcnow()
    _link_attempts.setdefault(uid, []).append(now)
    _cleanup_link_attempts()
    return len(_link_attempts.get(uid, []))


def get_app():
    global _app
    if _app is None:
        _app = create_app(scheduler_enabled=False)
    return _app


def get_bot() -> telebot.TeleBot:
    global bot
    if bot is None:
        token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
        if not token:
            raise RuntimeError('Задайте TELEGRAM_BOT_TOKEN в окружении или в .env')
        bot = telebot.TeleBot(token, parse_mode='HTML')
    return bot


def _user_for_telegram(telegram_user_id: int) -> User | None:
    return User.query.filter_by(telegram_user_id=telegram_user_id).first()


def _require_user(message) -> User | None:
    u = _user_for_telegram(message.from_user.id)
    if u:
        return u
    get_bot().reply_to(
        message,
        'Аккаунт не привязан. Откройте веб-приложение → Настройки → получите код и отправьте:\n'
        '<code>/link ВАШ_КОД</code>',
    )
    return None


def _cleanup_expired_codes():
    try:
        TelegramLinkCode.query.filter(TelegramLinkCode.expires_at < datetime.utcnow()).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error cleaning up expired codes: {e}")


def register_handlers() -> telebot.TeleBot:
    global _handlers_registered
    b = get_bot()
    if _handlers_registered:
        return b

    @b.message_handler(commands=['start'])
    def cmd_start(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            text = (
                '<b>SmartTo-DoList</b>\n\n'
                'Команды:\n'
                '/help — все команды\n'
                '/link КОД — привязать аккаунт (код в веб-настройках)\n'
                '/tasks — список задач\n'
                '/add текст — новая задача\n'
                '/stats — статистика\n'
            )
            b.reply_to(message, text)

    @b.message_handler(commands=['help'])
    def cmd_help(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            text = (
                '<b>Команды</b>\n'
                '/link <code>КОД</code> — связать Telegram с аккаунтом сайта\n'
                '/tasks — показать активные задачи (кнопки ниже сообщения)\n'
                '/add <i>название</i> — добавить задачу (или /add и затем текст сообщением)\n'
                '/stats — сколько задач всего и сколько выполнено\n'
                '/unlink — отвязать этот Telegram от аккаунта\n'
            )
            b.reply_to(message, text)

    @b.message_handler(commands=['link'])
    def cmd_link(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            parts = (message.text or '').split(maxsplit=1)
            if len(parts) < 2:
                b.reply_to(message, 'Использование: <code>/link КОД</code> (код из веб-настроек)')
                return
            code = parts[1].strip().upper()
            if not re.match(r'^[A-F0-9]{16}$', code):
                b.reply_to(message, 'Неверный формат кода. Нужен 16 символов (буквы A-F и цифры 0-9).')
                return

            if _register_link_attempt(message.from_user.id) > MAX_LINK_ATTEMPTS:
                b.reply_to(
                    message,
                    'Слишком много попыток привязки. Повторите через 15 минут.',
                )
                return

            _cleanup_expired_codes()
            row = TelegramLinkCode.query.filter_by(code=code).first()
            if not row or row.expires_at < datetime.utcnow():
                b.reply_to(message, 'Код не найден или истёк. Сгенерируйте новый в настройках сайта.')
                return

            tg_id = message.from_user.id
            existing = User.query.filter_by(telegram_user_id=tg_id).first()
            if existing and existing.id != row.user_id:
                b.reply_to(
                    message,
                    'Этот Telegram уже привязан к другому аккаунту. Отвяжите его в настройках того аккаунта.',
                )
                return

            user = User.query.get(row.user_id)
            if not user:
                b.reply_to(message, 'Ошибка: пользователь не найден.')
                return

            try:
                if user.telegram_user_id and user.telegram_user_id != tg_id:
                    user.telegram_user_id = None

                user.telegram_user_id = tg_id
                TelegramLinkCode.query.filter_by(user_id=user.id).delete()
                db.session.commit()
                
                logger.info(f"Telegram linked for user {user.username}")
                b.reply_to(message, f'Аккаунт <b>{html.escape(user.username)}</b> успешно привязан.')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error linking telegram: {e}")
                b.reply_to(message, 'Произошла ошибка при привязке аккаунта.')

    @b.message_handler(commands=['unlink'])
    def cmd_unlink(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            u = _user_for_telegram(message.from_user.id)
            if not u:
                b.reply_to(message, 'Telegram не был привязан.')
                return
            
            try:
                u.telegram_user_id = None
                TelegramLinkCode.query.filter_by(user_id=u.id).delete()
                db.session.commit()
                b.reply_to(message, 'Telegram отвязан. Вы можете привязать аккаунт снова через сайт.')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error unlinking telegram: {e}")
                b.reply_to(message, 'Произошла ошибка при отвязке аккаунта.')

    @b.message_handler(commands=['stats'])
    def cmd_stats(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            total = Task.query.filter_by(user_id=user.id).count()
            done = Task.query.filter_by(user_id=user.id, status='completed').count()
            b.reply_to(
                message,
                f'Всего задач: <b>{total}</b>\nВыполнено: <b>{done}</b>\nАктивных: <b>{total - done}</b>',
            )

    def _send_task_page(chat_id, user: User, page: int, message_id=None):
        q = (
            Task.query.filter_by(user_id=user.id)
            .filter(Task.status != 'completed')
            .order_by(Task.created_at.desc())
        )
        tasks = q.all()
        total = len(tasks)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        page = max(0, min(page, pages - 1))
        start = page * PAGE_SIZE
        chunk = tasks[start : start + PAGE_SIZE]

        if not chunk and page == 0:
            body = 'Нет активных задач. Добавьте: <code>/add Название</code>'
            kb = None
        else:
            body = '<b>Активные задачи:</b>\n\n'
            kb = types.InlineKeyboardMarkup()
            for t in chunk:
                due = ''
                if t.due_date:
                    try:
                        # Конвертируем в часовой пояс пользователя для отображения
                        user_tz = pytz.timezone(user.timezone or 'UTC')
                        local_due = t.due_date.astimezone(user_tz)
                        due = f' · до {local_due.strftime("%d.%m %H:%M")}'
                    except Exception:
                        due = f' · до {t.due_date.strftime("%d.%m %H:%M")}'

                pr = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t.priority or '', '⚪')
                body += f'{pr} <b>#{t.id}</b> {html.escape(t.title or "")}{html.escape(due)}\n'
                
                # Добавляем кнопки для каждой задачи
                kb.row(
                    types.InlineKeyboardButton(f"✅ Готово", callback_data=f'd:{t.id}'),
                    types.InlineKeyboardButton(f"✏️", callback_data=f'edit:{t.id}'),
                    types.InlineKeyboardButton(f"🗑️", callback_data=f'x:{t.id}')
                )
            
            body += f'\nСтр. {page + 1}/{pages}'
            
            nav_row = []
            if page > 0:
                nav_row.append(types.InlineKeyboardButton('◀️ Назад', callback_data=f'p:{page - 1}'))
            if page < pages - 1:
                nav_row.append(types.InlineKeyboardButton('Вперед ▶️', callback_data=f'p:{page + 1}'))
            if nav_row:
                kb.row(*nav_row)

        if message_id:
            try:
                b.edit_message_text(body, chat_id=chat_id, message_id=message_id, reply_markup=kb)
            except Exception as e:
                logger.debug('edit_message_text: %s', e)
                b.send_message(chat_id, body, reply_markup=kb)
        else:
            b.send_message(chat_id, body, reply_markup=kb)

    @b.message_handler(commands=['tasks'])
    def cmd_tasks(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            _send_task_page(message.chat.id, user, 0)

    @b.message_handler(commands=['add'])
    def cmd_add(message):
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            text = message.text or ''
            parts = text.split(maxsplit=1)
            if len(parts) >= 2 and parts[1].strip():
                _clear_pending(message.from_user.id)
            if len(parts) < 2 or not parts[1].strip():
                _pending_add_title[message.from_user.id] = True
                b.reply_to(message, 'Введите название задачи одним сообщением (до 200 символов):')
                return
            title = parts[1].strip()[:200]
            task = Task(title=title, user_id=user.id, priority='medium')
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}')

    @b.callback_query_handler(func=lambda c: True)
    def on_callback(call):
        _clear_pending(call.from_user.id)
        with get_app().app_context():
            user = _user_for_telegram(call.from_user.id)
            if not user:
                try:
                    b.answer_callback_query(call.id, 'Сначала привяжите аккаунт: /link', show_alert=True)
                except Exception:
                    pass
                return
            
            data = call.data or ''
            action, value = data.split(':', 1)

            if action == 'p': # Пагинация
                page = int(value)
                _send_task_page(call.message.chat.id, user, page, call.message.message_id)
                b.answer_callback_query(call.id)
                return

            task_id = int(value)
            task = Task.query.filter_by(id=task_id, user_id=user.id).first()
            if not task:
                b.answer_callback_query(call.id, 'Задача не найдена или уже обработана.', show_alert=True)
                # Обновляем список, чтобы убрать "мертвые" кнопки
                _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                return

            if action == 'd': # Выполнено
                task.complete()
                db.session.commit()
                b.answer_callback_query(call.id, f'Задача #{task.id} выполнена!')
                _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
            
            elif action == 'x': # Удалить
                db.session.delete(task)
                db.session.commit()
                b.answer_callback_query(call.id, f'Задача #{task.id} удалена.')
                _send_task_page(call.message.chat.id, user, 0, call.message.message_id)

            elif action == 'edit': # Редактировать
                b.answer_callback_query(call.id)
                b.send_message(call.message.chat.id, f"Для редактирования задачи #{task.id} воспользуйтесь веб-интерфейсом.")

            elif action == 'snooze': # Отложить
                minutes = int(value.split(':')[1])
                task.due_date = datetime.now(timezone.utc) + timedelta(minutes=minutes)
                db.session.commit()
                b.answer_callback_query(call.id, f'Задача отложена на {minutes} минут.')
                b.delete_message(call.message.chat.id, call.message.message_id)

            else:
                b.answer_callback_query(call.id)

    @b.message_handler(content_types=['text'], func=lambda m: m.chat.type == 'private')
    def on_plain_text(message):
        uid = message.from_user.id
        if uid not in _pending_add_title:
            return
        del _pending_add_title[uid]
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            title = (message.text or '').strip()[:200]
            if not title:
                b.reply_to(message, 'Пустой текст — задача не создана.')
                return
            task = Task(title=title, user_id=user.id, priority='medium')
            db.session.add(task)
            db.session.commit()
            b.reply_to(message, f'Задача добавлена: <b>#{task.id}</b> {html.escape(title)}')

    _handlers_registered = True
    return b


def generate_local_reminder_text(*, title: str, description: str | None, due_iso: str | None, priority: str | None) -> str:
    """Генерирует текст напоминания локально."""
    text = f"⏰ <b>Напоминание:</b> задача «{html.escape(title)}»"
    if due_iso:
        try:
            dt = datetime.fromisoformat(due_iso)
            time_str = dt.strftime("%H:%M")
            text += f" должна быть выполнена к {time_str}"
        except ValueError:
            pass
    if priority and priority in ['high', 'высокий']:
        text += " ❗️"
    
    text += "!"
    return text

def _start_reminder_loop(poll_seconds: int = 60):
    """
    Фоновый цикл автосообщений для due_date.
    Запускать один раз при старте бота.
    """
    import threading
    import time
    import pytz

    def loop():
        from app.models import ReminderLog

        window_minutes = int(os.environ.get("REMIND_WINDOW_MINUTES", "30").strip() or "30")
        reminder_type = "due_soon"
        dedup_minutes = int(os.environ.get("REMIND_DEDUP_MINUTES", "1440").strip() or "1440")

        while True:
            now_utc = datetime.now(timezone.utc)
            cutoff = now_utc + timedelta(minutes=window_minutes)

            try:
                with get_app().app_context():
                    tasks = Task.query.filter(Task.status != 'completed').filter(Task.due_date.isnot(None)).filter(Task.due_date <= cutoff).all()

                    for task in tasks:
                        user = task.owner
                        if not user or not user.telegram_user_id:
                            continue

                        existing = ReminderLog.query.filter_by(task_id=task.id, reminder_type=reminder_type, user_id=user.id).order_by(ReminderLog.reminded_at.desc()).first()
                        if existing and (datetime.utcnow() - existing.reminded_at).total_seconds() < dedup_minutes * 60:
                            continue

                        try:
                            user_tz = pytz.timezone(user.timezone or 'UTC')
                            local_due = task.due_date.astimezone(user_tz)
                            due_str = local_due.strftime("%H:%M")
                            reminder_text = f"⏰ Напоминание: задача «<b>{html.escape(task.title)}</b>» должна быть выполнена к {due_str}!"
                            
                            kb = types.InlineKeyboardMarkup()
                            kb.row(
                                types.InlineKeyboardButton("✅ Выполнено", callback_data=f"d:{task.id}"),
                                types.InlineKeyboardButton("⏰ Отложить на час", callback_data=f"snooze:{task.id}:60")
                            )
                            
                            get_bot().send_message(int(user.telegram_user_id), reminder_text, reply_markup=kb)
                            
                            new_log = ReminderLog(task_id=task.id, user_id=user.id, reminder_type=reminder_type, payload=reminder_text)
                            db.session.add(new_log)
                            db.session.commit()
                            
                        except Exception as e:
                            logger.warning("Telegram send failed for user_id=%s task_id=%s: %s", user.id, task.id, e)
                            db.session.rollback()

            except Exception as e:
                logger.exception("Reminder loop error: %s", str(e))

            time.sleep(poll_seconds)

    thread = threading.Thread(target=loop, daemon=True, name="reminder-loop")
    thread.start()
    return thread


def run_polling():
    logging.basicConfig(level=logging.INFO)
    try:
        from dotenv import load_dotenv
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        load_dotenv(os.path.join(root, '.env'))
    except ImportError:
        pass
    b = register_handlers()

    # Запускаем цикл напоминаний
    _start_reminder_loop()

    logger.info('Бот запущен (long polling). Остановка: Ctrl+C')
    b.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)