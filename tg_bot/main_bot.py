"""
Обработчики Telegram-бота: привязка аккаунта, список задач, добавление, выполнение, удаление.
Требуется переменная окружения TELEGRAM_BOT_TOKEN.
"""
from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime, timedelta

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
    with db.session.begin():
        TelegramLinkCode.query.filter(TelegramLinkCode.expires_at < datetime.utcnow()).delete(synchronize_session=False)


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
                '/done НОМЕР — отметить выполненной\n'
                '/del НОМЕР — удалить\n'
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
                '/done <i>id</i> — выполнить задачу по номеру из списка /tasks\n'
                '/del <i>id</i> — удалить задачу\n'
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

            with db.session.begin():
                if user.telegram_user_id and user.telegram_user_id != tg_id:
                    user.telegram_user_id = None
                    db.session.flush()

                user.telegram_user_id = tg_id
                TelegramLinkCode.query.filter_by(user_id=user.id).delete(synchronize_session=False)

            logger.info(f"Telegram linked for user {user.username}")
            b.reply_to(message, f'Аккаунт <b>{html.escape(user.username)}</b> успешно привязан.')

    @b.message_handler(commands=['unlink'])
    def cmd_unlink(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            u = _user_for_telegram(message.from_user.id)
            if not u:
                b.reply_to(message, 'Telegram не был привязан.')
                return
            with db.session.begin():
                u.telegram_user_id = None
                TelegramLinkCode.query.filter_by(user_id=u.id).delete(synchronize_session=False)
            b.reply_to(message, 'Telegram отвязан. Вы можете привязать аккаунт снова через сайт.')

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

        lines = []
        for t in chunk:
            due = ''
            if t.due_date:
                due = f' · до {t.due_date.strftime("%d.%m %H:%M")}'
            pr = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(t.priority or '', '⚪')
            lines.append(
                f'{pr} <b>#{t.id}</b> {html.escape(t.title or "")}{html.escape(due)}'
            )
        if not lines:
            body = 'Нет активных задач. Добавьте: <code>/add Название</code>'
        else:
            body = '\n'.join(lines) + f'\n\nСтр. {page + 1}/{pages} · всего активных: {total}'

        kb = types.InlineKeyboardMarkup(row_width=3)
        buttons = []
        for t in chunk:
            buttons.append(
                types.InlineKeyboardButton(text=f'✓{t.id}', callback_data=f'd:{t.id}')
            )
            buttons.append(
                types.InlineKeyboardButton(text=f'✕{t.id}', callback_data=f'x:{t.id}')
            )
        if buttons:
            kb.add(*buttons)
        nav_row = []
        if page > 0:
            nav_row.append(types.InlineKeyboardButton('◀', callback_data=f'p:{page - 1}'))
        if page < pages - 1:
            nav_row.append(types.InlineKeyboardButton('▶', callback_data=f'p:{page + 1}'))
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

    @b.message_handler(commands=['done'])
    def cmd_done(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            parts = (message.text or '').split()
            if len(parts) < 2 or not parts[1].isdigit():
                b.reply_to(message, 'Использование: <code>/done ID</code> (номер из списка /tasks)')
                return
            tid = int(parts[1])
            task = Task.query.filter_by(id=tid, user_id=user.id).first()
            if not task:
                b.reply_to(message, 'Задача не найдена.')
                return
            task.complete()
            db.session.commit()
            b.reply_to(message, f'Выполнено: #{tid} {html.escape(task.title)}')

    @b.message_handler(commands=['del'])
    def cmd_del(message):
        _clear_pending(message.from_user.id)
        with get_app().app_context():
            user = _require_user(message)
            if not user:
                return
            parts = (message.text or '').split()
            if len(parts) < 2 or not parts[1].isdigit():
                b.reply_to(message, 'Использование: <code>/del ID</code>')
                return
            tid = int(parts[1])
            task = Task.query.filter_by(id=tid, user_id=user.id).first()
            if not task:
                b.reply_to(message, 'Задача не найдена.')
                return
            title = task.title
            db.session.delete(task)
            db.session.commit()
            b.reply_to(message, f'Удалено: #{tid} {html.escape(title or "")}')

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
            if data.startswith('p:'):
                page = int(data.split(':')[1])
                _send_task_page(call.message.chat.id, user, page, call.message.message_id)
                b.answer_callback_query(call.id)
                return
            if data.startswith('d:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    task.complete()
                    db.session.commit()
                    b.answer_callback_query(call.id, 'Готово')
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    b.answer_callback_query(call.id, 'Не найдено')
                return
            if data.startswith('x:'):
                tid = int(data.split(':')[1])
                task = Task.query.filter_by(id=tid, user_id=user.id).first()
                if task:
                    db.session.delete(task)
                    db.session.commit()
                    b.answer_callback_query(call.id, 'Удалено')
                    _send_task_page(call.message.chat.id, user, 0, call.message.message_id)
                else:
                    b.answer_callback_query(call.id, 'Не найдено')
                return
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
        # Пытаемся распарсить дату для более красивого вывода
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

    def loop():
        from app.models import ReminderLog  # локально чтобы не ломать импорт

        window_minutes = int(os.environ.get("REMIND_WINDOW_MINUTES", "30").strip() or "30")
        reminder_type = "due_soon"

        # Чтобы не отправлять повторно бесконечно: ограничиваем интервал (в минутах)
        dedup_minutes = int(os.environ.get("REMIND_DEDUP_MINUTES", "1440").strip() or "1440")

        while True:
            now = datetime.utcnow()
            cutoff = now + timedelta(minutes=window_minutes)

            try:
                with get_app().app_context():
                    tasks = (  # type: ignore[misc]
                        Task.query.filter(Task.status != 'completed')  # type: ignore[misc]
                        .filter(Task.due_date.isnot(None))  # type: ignore[misc]
                        .filter(Task.due_date <= cutoff)  # type: ignore[misc]
                        .all()
                    )

                    for task in tasks:
                        # Если уже давно просрочено — тоже шлём как "due_soon" (тип можно расширять позже)
                        user = task.owner
                        if not user or not user.telegram_user_id:
                            continue

                        existing = (
                            ReminderLog.query.filter_by(
                                task_id=task.id,
                                reminder_type=reminder_type,
                                user_id=user.id,
                            )
                            .order_by(ReminderLog.reminded_at.desc())
                            .first()
                        )
                        if existing:
                            age = datetime.utcnow() - existing.reminded_at
                            if age.total_seconds() < dedup_minutes * 60:
                                continue

                        reminder_text = generate_local_reminder_text(
                            title=task.title or "",
                            description=task.description or "",
                            due_iso=task.due_date.isoformat() if task.due_date else None,
                            priority=task.priority,
                        )

                        try:
                            # Текст уже содержит нужный HTML, не эскейпим его дополнительно
                            get_bot().send_message(int(user.telegram_user_id), reminder_text)
                        except Exception as e:
                            logger.warning(
                                "Telegram send failed for user_id=%s task_id=%s: %s",
                                user.id,
                                task.id,
                                e,
                            )
                            continue

                        row = ReminderLog(  # type: ignore[misc]
                            task_id=task.id,
                            user_id=user.id,
                            reminder_type=reminder_type,
                            payload=reminder_text,
                        )
                        db.session.add(row)
                        db.session.commit()
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